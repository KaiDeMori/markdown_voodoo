// calm_comms, Rabenschnack 1.6 in Go: watches a raven's Hrafnsmal seat and sends its mail.
// on: keeps watching.md while it watches, and wakes the raven on the first new mail, or when the long or short timer runs out.
// A waking watcher leaves watching.md saying awake for a few minutes, until the raven's next on replaces it.
// off: asks the seat's watcher to stop, and deletes watching.md.
// overview: lists every seat with its mailbox: the door is open while a raven watches, and the flag is up while mail waits.
// inbox: prints waiting mail, oldest first, up to a number and a size limit, and moves it into already_read.
// send: writes a mail from one seat into another, never overwrites a mail, and answers with the target's mailbox.
// group: writes a mail from one seat to every other member of a group, and keeps a copy as the group's thread.
// join and leave: create or delete a seat's own file in a group's members folder, and wake nobody.
// calm-comms is for ravens: every line it prints is for a raven to read.
// Usage: calm_comms on <seat_name> [long|short|<minutes>]
//        calm_comms off <seat_name>
//        calm_comms overview
//        calm_comms inbox <seat_name> [mail_limit]
//        calm_comms send <seat_name> <target_seat_name> <text>
//        calm_comms group <seat_name> <group_name> <text>
//        calm_comms join <seat_name> <group_name>
//        calm_comms leave <seat_name> <group_name>

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

var (
	// The live hall, unless a test names a haven of its own in calm_comms_haven_location.
	haven_location     = haven()
	hrafnsmal_location = filepath.Join(haven_location, "Hall", "thing", "Hrafnsmal")
	// Each group is a folder here: its members folder holds one empty file per member, named after the seat, and the group's folder keeps the thread.
	group_chat_location = filepath.Join(haven_location, "Hall", "thing", "group_chat")
	// The watcher hears of new mail at once; it still looks this often, as a safety net for lost notifications.
	poll_interval_seconds = 10
	long_watcher_minutes  = 55
	short_watcher_minutes = 4
	// A raven that just woke stays awake in the overview this long; one in a long turn re-arms only when that turn ends.
	awake_grace_minutes        = 5
	inbox_mail_limit           = 3
	inbox_size_limit_kilobytes = 10
	write_throttle_seconds     = 2
)

// Exit codes: callers only tell zero from not zero, and the line says why.
// 2 belongs to Go: the tool itself broke.
const (
	// Not done: refused, or the system refused a file; the line says why.
	exit_refused = 1
	// Stopped: no mail, nothing to do.
	exit_stopped = 143
	// No such seat: its README is missing.
	// Easter egg: 5040 is on purpose; bash sees it modulo 256, the 176 in SKILL.md.
	exit_no_such_seat = 5040
)

// What the command line says, and where it leads.
var (
	verb                          string
	seat_name                     string
	seat_location                 string
	watching_marker_file_location string
	already_read_location         string
)

func main() {
	verb = argument(1)
	seat_name = argument(2)
	seat_location = filepath.Join(hrafnsmal_location, seat_name)
	watching_marker_file_location = filepath.Join(seat_location, "watching.md")
	already_read_location = filepath.Join(seat_location, "already_read")
	switch verb {
	case "on":
		watcher_length := argument(3)
		if watcher_length == "" {
			watcher_length = "long"
		}
		start_watcher(watcher_length)
	case "off":
		stop_watcher()
	case "overview":
		show_overview()
	case "inbox":
		check_seat(seat_name)
		show_inbox(read_mail_limit())
	case "send":
		target_seat_name := argument(3)
		check_seat(seat_name)
		// A group mail reaches every member, so it has a verb of its own; a seat of the same name still goes first.
		if target_seat_name != "" && !is_file(filepath.Join(hrafnsmal_location, target_seat_name, "README.md")) && is_folder(filepath.Join(group_chat_location, target_seat_name, "members")) {
			fmt.Printf("%s is a group: a mail there reaches every member. Use group.\n", target_seat_name)
			os.Exit(exit_refused)
		}
		check_seat(target_seat_name)
		send_mail(target_seat_name, text_from(4))
	case "group":
		group_name := argument(3)
		check_seat(seat_name)
		check_group(group_name)
		send_group(group_name, text_from(4))
	case "join", "leave":
		group_name := argument(3)
		check_seat(seat_name)
		check_group(group_name)
		if verb == "join" {
			join_group(group_name)
		} else {
			leave_group(group_name)
		}
	default:
		fmt.Println("on, off, overview, inbox, send, group, join or leave?")
		os.Exit(exit_refused)
	}
}

// argument is the command line's word at a place, or nothing, like an unset $1 in bash.
func argument(place int) string {
	if place < len(os.Args) {
		return os.Args[place]
	}
	return ""
}

// text_from joins every word from a place on, as $* does in bash.
func text_from(place int) string {
	if place >= len(os.Args) {
		return ""
	}
	return strings.Join(os.Args[place:], " ")
}

// haven is the live C:/haven, unless a test names a haven of its own in calm_comms_haven_location.
func haven() string {
	if test_haven_location := os.Getenv("calm_comms_haven_location"); test_haven_location != "" {
		return test_haven_location
	}
	return "C:/haven"
}

// timestamp writes a moment the way the hall does, such as 2026-10-16T14:15+02:00.
func timestamp(moment time.Time) string {
	return moment.Format("2006-01-02T15:04-07:00")
}

func check_seat(name string) {
	if name == "" || !is_file(filepath.Join(hrafnsmal_location, name, "README.md")) {
		fmt.Printf("Quoth the raven: README in %s? Nevermore.\n", name)
		os.Exit(exit_no_such_seat)
	}
}

func throttle() {
	// A busy hall gets a buffer: a call that wrote waits a moment before it returns.
	time.Sleep(time.Duration(write_throttle_seconds) * time.Second)
}

func exists(location string) bool {
	_, failure := os.Stat(location)
	return failure == nil
}

func is_file(location string) bool {
	information, failure := os.Stat(location)
	return failure == nil && information.Mode().IsRegular()
}

func is_folder(location string) bool {
	information, failure := os.Stat(location)
	return failure == nil && information.IsDir()
}

// must hands on a value, and check lets a call pass, unless the system met a problem: then the call ends with it, in one line.
func must[Value any](value Value, failure error) Value {
	check(failure)
	return value
}

func check(failure error) {
	if failure != nil {
		fmt.Println(failure)
		os.Exit(exit_refused)
	}
}
