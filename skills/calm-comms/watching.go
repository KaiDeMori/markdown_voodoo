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

var (
	own_PID              string
	watching_marker_file *os.File
	stop_request         = make(chan struct{})
	stop_request_once    sync.Once
	mail_hint            = make(chan struct{}, 1)
)

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

func stop_watcher() {
	check_seat(seat_name)
	file := take_over_seat()
	file.Close()
	os.Remove(watching_marker_file_location)
	throttle()
}

func take_over_seat() *os.File {
	file := must(os.OpenFile(watching_marker_file_location, os.O_RDWR|os.O_CREATE, 0o644))
	if try_lock(file, true) {
		return file
	}
	_, marker_PID, _ := read_marker(watching_marker_file_location)
	check(file.Truncate(0))
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

func write_marker(file *os.File, content string) {
	check(file.Truncate(0))
	must(file.WriteAt([]byte(content), 0))
}

func marker_names_this_watcher() bool {
	_, marker_PID, _ := read_marker(watching_marker_file_location)
	return marker_PID == own_PID
}

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

func start_listening() {
	signals := make(chan os.Signal, 1)
	signal.Notify(signals, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-signals
		request_stop()
	}()
	notifier, failure := fsnotify.NewWatcher()
	if failure == nil && notifier.Add(seat_location) == nil {
		go follow_seat(notifier)
	}
}

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
	}
}

func request_stop() {
	stop_request_once.Do(func() { close(stop_request) })
}

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
			rest(time.Second)
			if !exists(filepath.Join(seat_location, file_name)) {
				continue
			}
			fmt.Printf("%s mail: %s\n", timestamp(time.Now()), file_name)
			return
		}
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

func rest(duration time.Duration) {
	timer := time.NewTimer(duration)
	defer timer.Stop()
	select {
	case <-timer.C:
	case <-stop_request:
		stop()
	}
}

func stop() {
	fmt.Println("stopped")
	remove_own_marker()
	os.Exit(exit_stopped)
}

func remove_own_marker() {
	if !marker_names_this_watcher() {
		return
	}
	watching_marker_file.Close()
	os.Remove(watching_marker_file_location)
}

func leave_awake_marker() {
	if !marker_names_this_watcher() {
		return
	}
	awake_until := time.Now().Add(time.Duration(awake_grace_minutes) * time.Minute).Unix()
	write_marker(watching_marker_file, fmt.Sprintf("awake %d\n", awake_until))
}

func show_overview() {
	entries, _ := os.ReadDir(hall_mail_location)
	for _, entry := range entries {
		overview_seat_name := entry.Name()
		overview_seat_location := filepath.Join(hall_mail_location, overview_seat_name)
		if strings.HasPrefix(overview_seat_name, ".") || !is_folder(overview_seat_location) {
			continue
		}
		fmt.Printf("%s %s\n", overview_seat_name, mailbox(overview_seat_location))
	}
}

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

func is_watched(location string) bool {
	marker_location := filepath.Join(location, "watching.md")
	if is_held_by_watcher(marker_location) {
		return true
	}
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
