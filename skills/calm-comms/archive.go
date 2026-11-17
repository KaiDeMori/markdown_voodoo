package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const message_name_stamp_layout = "2006-01-02_150405"

func archive_read_messages() {
	if !archive_messages {
		return
	}
	dry_run := os.Getenv("calm_comms_archive_dry_run") != ""
	oldest_kept_moment := time.Now().AddDate(0, 0, -read_mail_kept_days)
	for _, seat := range folder_names(hrafnsmal_location) {
		seat_folder := filepath.Join(hrafnsmal_location, seat)
		if !is_file(filepath.Join(seat_folder, "README.md")) {
			continue
		}
		read_folder := filepath.Join(seat_folder, "already_read")
		for _, entry := range message_entries(read_folder) {
			if moment, known := message_moment(entry); known && moment.Before(oldest_kept_moment) {
				archive_message(read_folder, entry.Name(), filepath.Join(archive_location, "__mail", moment.Format("2006-01"), seat, "already_read"), dry_run)
			}
		}
	}
	for _, group := range folder_names(group_chat_location) {
		group_folder := filepath.Join(group_chat_location, group)
		if !is_folder(filepath.Join(group_folder, "members")) {
			continue
		}
		members := read_members(group)
		for _, entry := range message_entries(group_folder) {
			if moment, known := message_moment(entry); known && read_by_every_member(members, entry.Name()) {
				archive_message(group_folder, entry.Name(), filepath.Join(archive_location, "__group_chat", moment.Format("2006-01"), group), dry_run)
			}
		}
	}
}

func read_by_every_member(members []string, message_name string) bool {
	for _, member := range members {
		if exists(filepath.Join(hrafnsmal_location, member, message_name)) {
			return false
		}
	}
	return true
}

func archive_message(folder string, message_name string, archive_folder string, dry_run bool) {
	source_location := filepath.Join(folder, message_name)
	archived_location := filepath.Join(archive_folder, message_name)
	if exists(archived_location) {
		return
	}
	if dry_run {
		fmt.Printf("would move %s -> %s\n", filepath.ToSlash(source_location), filepath.ToSlash(archived_location))
		return
	}
	if os.MkdirAll(archive_folder, 0o755) == nil {
		os.Rename(source_location, archived_location)
	}
}

func message_entries(folder string) []os.DirEntry {
	entries, _ := os.ReadDir(folder)
	messages := []os.DirEntry{}
	for _, entry := range entries {
		name := entry.Name()
		if entry.Type().IsRegular() && !strings.HasPrefix(name, ".") && name != "README.md" && name != "watching.md" {
			messages = append(messages, entry)
		}
	}
	return messages
}

func message_moment(entry os.DirEntry) (time.Time, bool) {
	if name := entry.Name(); len(name) >= len(message_name_stamp_layout) {
		if moment, failure := time.ParseInLocation(message_name_stamp_layout, name[:len(message_name_stamp_layout)], time.Local); failure == nil {
			return moment, true
		}
	}
	information, failure := entry.Info()
	if failure != nil {
		return time.Time{}, false
	}
	return information.ModTime(), true
}

func folder_names(location string) []string {
	entries, _ := os.ReadDir(location)
	names := []string{}
	for _, entry := range entries {
		if entry.IsDir() && !strings.HasPrefix(entry.Name(), ".") {
			names = append(names, entry.Name())
		}
	}
	return names
}
