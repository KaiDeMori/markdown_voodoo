package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

var (
	haven_location             string
	hrafnsmal_location         string
	group_chat_location        string
	archive_location           string
	read_mail_kept_days        int
	poll_interval_seconds      int
	long_watcher_minutes       int
	short_watcher_minutes      int
	awake_grace_minutes        int
	inbox_mail_limit           int
	inbox_size_limit_kilobytes int
	write_throttle_seconds     int
)

const (
	exit_refused      = 1
	exit_stopped      = 143
	exit_no_such_seat = 5040
)

var (
	verb                          string
	seat_name                     string
	seat_location                 string
	watching_marker_file_location string
	already_read_location         string
)

func main() {
	read_settings()
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
		switch argument(2) {
		case "":
			show_overview()
		case "groups":
			show_groups(argument(3))
		default:
			fmt.Println("overview, or overview groups [group_name]?")
			os.Exit(exit_refused)
		}
	case "inbox":
		check_seat(seat_name)
		archive_read_messages()
		show_inbox(read_mail_limit())
	case "send":
		target_seat_name := argument(3)
		check_seat(seat_name)
		if target_seat_name != "" && !is_file(filepath.Join(hrafnsmal_location, target_seat_name, "README.md")) && is_folder(filepath.Join(group_chat_location, target_seat_name, "members")) {
			fmt.Printf("%s is a group: a mail there reaches every member. Use group.\n", target_seat_name)
			os.Exit(exit_refused)
		}
		check_seat(target_seat_name)
		archive_read_messages()
		send_mail(target_seat_name, text_from(4))
	case "group":
		group_name := argument(3)
		check_seat(seat_name)
		check_group(group_name)
		archive_read_messages()
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

func argument(place int) string {
	if place < len(os.Args) {
		return os.Args[place]
	}
	return ""
}

func text_from(place int) string {
	if place >= len(os.Args) {
		return ""
	}
	return strings.Join(os.Args[place:], " ")
}

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
