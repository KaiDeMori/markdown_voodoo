package main

import (
	"os"
	"path/filepath"
	"strings"
	"time"
)

const message_name_stamp_layout = "2006-01-02_150405"

func archive_read_messages() {
	oldest_kept_moment := time.Now().AddDate(0, 0, -read_mail_kept_days)
	for _, seat := range folder_names(hrafnsmal_location) {
		if is_file(filepath.Join(hrafnsmal_location, seat, "README.md")) {
			archive_old_messages(filepath.Join(hrafnsmal_location, seat, "already_read"), "mail", seat, oldest_kept_moment)
		}
	}
	for _, group := range group_names() {
		archive_old_messages(filepath.Join(group_chat_location, group, "already_read"), "group_chat", group, oldest_kept_moment)
	}
}

func archive_old_messages(read_folder string, message_kind string, owner_name string, oldest_kept_moment time.Time) {
	for _, entry := range message_entries(read_folder) {
		if moment, known := message_moment(entry); known && moment.Before(oldest_kept_moment) {
			move_message(read_folder, entry.Name(), filepath.Join(archive_location, moment.Format("2006-01"), message_kind, owner_name))
		}
	}
}

func move_message(folder string, message_name string, target_folder string) {
	target_location := filepath.Join(target_folder, message_name)
	if exists(target_location) {
		return
	}
	if os.MkdirAll(target_folder, 0o755) == nil {
		os.Rename(filepath.Join(folder, message_name), target_location)
	}
}

func group_names() []string {
	names := []string{}
	for _, name := range folder_names(group_chat_location) {
		if is_folder(filepath.Join(group_chat_location, name, "members")) {
			names = append(names, name)
		}
	}
	return names
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
