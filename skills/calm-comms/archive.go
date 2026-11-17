package main

import (
	"os"
	"path/filepath"
	"strings"
	"time"
)

// archive_old_messages moves every message older than archive_after_days out of the seats and the group threads, into the archive, sorted by the message's month.
// It rides on the calls that write anyway: a move that fails waits for the next call, and never stops the call it rides on.
func archive_old_messages() {
	border := time.Now().AddDate(0, 0, -archive_after_days)
	for _, seat := range folder_names(hrafnsmal_location) {
		seat_folder := filepath.Join(hrafnsmal_location, seat)
		if !is_file(filepath.Join(seat_folder, "README.md")) {
			continue
		}
		archive_folder(seat_folder, border, filepath.Join("mail", seat))
		archive_folder(filepath.Join(seat_folder, "already_read"), border, filepath.Join("mail", seat))
	}
	for _, group := range folder_names(group_chat_location) {
		group_folder := filepath.Join(group_chat_location, group)
		if is_folder(filepath.Join(group_folder, "members")) {
			archive_folder(group_folder, border, filepath.Join("group_chat", group))
		}
	}
}

// archive_folder moves the old messages at the top of one folder; README.md, watching.md, dotfiles and folders are no messages.
func archive_folder(folder string, border time.Time, archive_part string) {
	entries, failure := os.ReadDir(folder)
	if failure != nil {
		return
	}
	for _, entry := range entries {
		name := entry.Name()
		if !entry.Type().IsRegular() || strings.HasPrefix(name, ".") || name == "README.md" || name == "watching.md" {
			continue
		}
		moment, known := message_moment(entry)
		if !known || !moment.Before(border) {
			continue
		}
		target_folder := filepath.Join(archive_location, moment.Format("2006-01"), archive_part)
		target_location := filepath.Join(target_folder, name)
		// The archive never loses a message: a name that is already there keeps its place, and so does the newcomer.
		if exists(target_location) || os.MkdirAll(target_folder, 0o755) != nil {
			continue
		}
		os.Rename(filepath.Join(folder, name), target_location)
	}
}

// message_moment is the moment a mail's name begins with, such as 2026-10-16_141523, or the file's own time when its name has none.
func message_moment(entry os.DirEntry) (time.Time, bool) {
	if name := entry.Name(); len(name) >= len("2006-01-02_150405") {
		if moment, failure := time.ParseInLocation("2006-01-02_150405", name[:len("2006-01-02_150405")], time.Local); failure == nil {
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
