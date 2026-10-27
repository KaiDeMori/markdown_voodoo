package main

import (
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/fsnotify/fsnotify"
)

// A watcher holds a lock on its seat's watching.md for as long as it lives.
// The system lets go of a lock when its holder ends, even in a crash, so the lock says who is watching, and no process ID needs trust.
// A stop is a request: off and a newer on empty watching.md, and a watcher whose marker no longer names it stops at once.

var (
	own_PID              string
	watching_marker_file *os.File
	// stop_request closes once a signal says stop, or the marker no longer names this watcher.
	stop_request      = make(chan struct{})
	stop_request_once sync.Once
	// mail_hint holds one hint at most: a notification only says look now, and the seat itself says what is there.
	mail_hint = make(chan struct{}, 1)
)

// start_watcher runs on: it takes over the seat, waits for the first new mail or the timer, and leaves the seat awake.
func start_watcher(watcher_length string) {
	check_seat(seat_name)
	timer_minutes := 0
	switch {
	case watcher_length == "long":
		timer_minutes = long_watcher_minutes
	case watcher_length == "short":
		timer_minutes = short_watcher_minutes
	case !is_whole_number(watcher_length):
		fmt.Println("Long, short, or minutes?")
		os.Exit(exit_refused)
	default:
		timer_minutes = must(strconv.Atoi(watcher_length))
	}
	watching_marker_file = take_over_seat()
	own_PID = strconv.Itoa(os.Getpid())
	until := timestamp(time.Now().Add(time.Duration(timer_minutes) * time.Minute))
	write_marker(watching_marker_file, "until "+until+"\npid "+own_PID+"\n")
	start_listening()
	watch_seat(timer_minutes)
	leave_awake_marker()
}

// stop_watcher runs off: it stops the seat's watcher, and deletes watching.md, an awake marker as well.
func stop_watcher() {
	check_seat(seat_name)
	file := take_over_seat()
	// Windows deletes no file that is still open.
	file.Close()
	os.Remove(watching_marker_file_location)
	throttle()
}

// take_over_seat opens watching.md and takes its lock; a living watcher is asked to stop first.
// Quiet when there is nothing to do, two words after a cleanup, and one calm line otherwise.
func take_over_seat() *os.File {
	file := must(os.OpenFile(watching_marker_file_location, os.O_RDWR|os.O_CREATE, 0o644))
	if try_lock(file, true) {
		return file
	}
	_, marker_PID, _ := read_marker(watching_marker_file_location)
	// An empty marker names nobody, and its watcher reads that as stop.
	check(file.Truncate(0))
	// The watcher hears of it at once, or at its next look at the latest.
	deadline := time.Now().Add(time.Duration(poll_interval_seconds+5) * time.Second)
	for time.Now().Before(deadline) {
		time.Sleep(100 * time.Millisecond)
		if try_lock(file, true) {
			fmt.Println("cleanup done")
			return file
		}
	}
	fmt.Printf("The old watcher, process %s, could not be stopped.\n", marker_PID)
	os.Exit(exit_refused)
	return nil
}

// read_marker reads watching.md: the moment the timer runs out, and the watcher's process ID.
// After a wake it holds only awake, and the second its grace ends.
func read_marker(location string) (marker_until string, marker_PID string, marker_awake string) {
	content, failure := os.ReadFile(location)
	if failure != nil {
		return "", "", ""
	}
	for _, line := range strings.Split(string(content), "\n") {
		switch {
		case strings.HasPrefix(line, "until "):
			marker_until = strings.TrimPrefix(line, "until ")
		case strings.HasPrefix(line, "pid "):
			marker_PID = strings.TrimPrefix(line, "pid ")
		case strings.HasPrefix(line, "awake "):
			marker_awake = strings.TrimPrefix(line, "awake ")
		}
	}
	return marker_until, marker_PID, marker_awake
}

// write_marker replaces what watching.md says, through the handle that holds the lock.
func write_marker(file *os.File, content string) {
	check(file.Truncate(0))
	must(file.WriteAt([]byte(content), 0))
}

func marker_names_this_watcher() bool {
	_, marker_PID, _ := read_marker(watching_marker_file_location)
	return marker_PID == own_PID
}

// is_held_by_watcher tells whether a living watcher holds the lock on watching.md.
// A look takes a shared lock for a moment, so two looks at the same moment never disturb each other.
func is_held_by_watcher(location string) bool {
	file, failure := os.Open(location)
	if failure != nil {
		return false
	}
	defer file.Close()
	if !try_lock(file, false) {
		return true
	}
	unlock(file)
	return false
}

// start_listening gathers what can end a watch early, a signal and a stop request, and the hints of new mail.
func start_listening() {
	signals := make(chan os.Signal, 1)
	signal.Notify(signals, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-signals
		request_stop()
	}()
	// Notifications make the watcher quick, and the poll keeps it sure: notifications get lost when their buffer overflows.
	notifier, failure := fsnotify.NewWatcher()
	if failure == nil && notifier.Add(seat_location) == nil {
		go follow_seat(notifier)
	}
}

// follow_seat turns notifications into hints: a change to watching.md may be a stop request, and any other change may be mail.
func follow_seat(notifier *fsnotify.Watcher) {
	for {
		select {
		case event, open := <-notifier.Events:
			if !open {
				return
			}
			if filepath.Base(event.Name) != "watching.md" {
				hint_mail()
			} else if !marker_names_this_watcher() {
				request_stop()
			}
		case _, open := <-notifier.Errors:
			if !open {
				return
			}
			// A lost notification costs nothing: look again now.
			if !marker_names_this_watcher() {
				request_stop()
			}
			hint_mail()
		}
	}
}

func hint_mail() {
	select {
	case mail_hint <- struct{}{}:
	default:
		// A hint is already waiting, and one is enough.
	}
}

func request_stop() {
	stop_request_once.Do(func() { close(stop_request) })
}

// watch_seat waits for the first new mail, or for the timer.
func watch_seat(timer_minutes int) {
	known_files := map[string]bool{}
	for _, file_name := range seat_file_names() {
		known_files[file_name] = true
	}
	timer := time.After(time.Duration(timer_minutes) * time.Minute)
	for {
		for _, file_name := range seat_file_names() {
			if file_name == "README.md" || file_name == "watching.md" || known_files[file_name] {
				continue
			}
			// A writer's temp file is gone a second later; only a file that stays is mail.
			rest(time.Second)
			if !exists(filepath.Join(seat_location, file_name)) {
				continue
			}
			fmt.Printf("%s mail: %s\n", timestamp(time.Now()), file_name)
			// A raven wakes on the first mail.
			return
		}
		// Every look also catches a stop request whose notification got lost.
		if !marker_names_this_watcher() {
			stop()
		}
		poll := time.NewTimer(time.Duration(poll_interval_seconds) * time.Second)
		select {
		case <-mail_hint:
		case <-poll.C:
		case <-timer:
			fmt.Printf("%s timer\n", timestamp(time.Now()))
			return
		case <-stop_request:
			stop()
		}
		poll.Stop()
	}
}

// seat_file_names lists the files at the top of the seat; like the bash glob before it, it passes over dotfiles.
func seat_file_names() []string {
	entries, failure := os.ReadDir(seat_location)
	if failure != nil {
		return nil
	}
	file_names := []string{}
	for _, entry := range entries {
		if !strings.HasPrefix(entry.Name(), ".") && is_file(filepath.Join(seat_location, entry.Name())) {
			file_names = append(file_names, entry.Name())
		}
	}
	return file_names
}

// rest waits, and a stop still acts at once.
func rest(duration time.Duration) {
	timer := time.NewTimer(duration)
	defer timer.Stop()
	select {
	case <-timer.C:
	case <-stop_request:
		stop()
	}
}

// stop ends a watch early; 143 is the usual exit code after a stop, and the raven reads it as: no mail, nothing to do.
func stop() {
	fmt.Println("stopped")
	remove_own_marker()
	os.Exit(exit_stopped)
}

// remove_own_marker deletes watching.md only while it is still the watcher's own, never a newer watcher's.
func remove_own_marker() {
	if !marker_names_this_watcher() {
		return
	}
	// Windows deletes no file that is still open.
	watching_marker_file.Close()
	os.Remove(watching_marker_file_location)
}

// leave_awake_marker: a raven that just woke is about to watch again, so its seat shows awake instead of gone until its next on.
// The awake marker names no process, so off and the next on simply replace it.
func leave_awake_marker() {
	if !marker_names_this_watcher() {
		return
	}
	awake_until := time.Now().Add(time.Duration(awake_grace_minutes) * time.Minute).Unix()
	write_marker(watching_marker_file, fmt.Sprintf("awake %d\n", awake_until))
}

// show_overview lists every seat with its mailbox, one line each, such as: huginn 📭
func show_overview() {
	entries, _ := os.ReadDir(hrafnsmal_location)
	for _, entry := range entries {
		overview_seat_name := entry.Name()
		overview_seat_location := filepath.Join(hrafnsmal_location, overview_seat_name)
		if strings.HasPrefix(overview_seat_name, ".") || !is_folder(overview_seat_location) {
			continue
		}
		fmt.Printf("%s %s\n", overview_seat_name, mailbox(overview_seat_location))
	}
}

// mailbox shows a seat at a glance: the door is open while a raven watches, and the flag is up while mail waits.
// 📬 watching, mail waiting; 📭 watching, nothing waiting; 📫 not watching, mail waiting; 📪 not watching, nothing waiting.
func mailbox(location string) string {
	watched := is_watched(location)
	waiting := has_waiting_mail(location)
	switch {
	case watched && waiting:
		return "📬"
	case watched:
		return "📭"
	case waiting:
		return "📫"
	default:
		return "📪"
	}
}

// is_watched tells whether a raven watches a seat: a living watcher holds the lock on its watching.md, or a raven that just woke is about to watch again.
func is_watched(location string) bool {
	marker_location := filepath.Join(location, "watching.md")
	if is_held_by_watcher(marker_location) {
		return true
	}
	// An awake marker counts while its grace lasts.
	_, _, marker_awake := read_marker(marker_location)
	awake_until, failure := strconv.ParseInt(marker_awake, 10, 64)
	return failure == nil && is_whole_number(marker_awake) && time.Now().Unix() < awake_until
}

func is_whole_number(text string) bool {
	if text == "" {
		return false
	}
	for _, character := range text {
		if character < '0' || character > '9' {
			return false
		}
	}
	return true
}
