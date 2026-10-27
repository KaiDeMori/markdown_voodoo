package main

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"time"
)

// read_mail_limit reads inbox's mail limit; without one, the default applies.
func read_mail_limit() int {
	limit_text := argument(3)
	if limit_text == "" {
		return inbox_mail_limit
	}
	mail_limit, failure := strconv.Atoi(limit_text)
	if failure != nil {
		fmt.Println("inbox <seat_name> [mail_limit]?")
		os.Exit(exit_refused)
	}
	return mail_limit
}

// show_inbox prints waiting mail, oldest first, up to a number and a size limit, and moves it into already_read.
func show_inbox(mail_limit int) {
	mail_count, used_bytes, waiting_count := 0, int64(0), 0
	waiting_list := []string{}
	for _, mail := range waiting_mail() {
		// The first mail of a call always comes, so a big one arrives alone.
		if waiting_count > 0 || mail_count == mail_limit || (mail_count > 0 && used_bytes+mail.Size() > int64(inbox_size_limit_kilobytes)*1024) {
			waiting_count++
			waiting_list = append(waiting_list, fmt.Sprintf("%s (%s)", mail.Name(), size_text(mail.Size())))
			continue
		}
		if exists(filepath.Join(already_read_location, mail.Name())) {
			fmt.Printf("Deja lu: %s\n", mail.Name())
			os.Exit(exit_refused)
		}
		mail_location := filepath.Join(seat_location, mail.Name())
		content := must(os.ReadFile(mail_location))
		fmt.Printf("--- %s\n", mail.Name())
		os.Stdout.Write(content)
		// A mail without a final line break still gets its own line end, so the next header stays apart.
		if len(content) > 0 && content[len(content)-1] != '\n' {
			fmt.Println()
		}
		fmt.Println()
		check(os.MkdirAll(already_read_location, 0o755))
		check(os.Rename(mail_location, filepath.Join(already_read_location, mail.Name())))
		mail_count++
		used_bytes += mail.Size()
	}
	if waiting_count > 0 && mail_count > 0 {
		fmt.Printf("%d more waiting: %s\n", waiting_count, strings.Join(waiting_list, ", "))
	}
	if waiting_count > 0 && mail_count == 0 {
		fmt.Printf("%d waiting: %s\n", waiting_count, strings.Join(waiting_list, ", "))
	}
	if mail_count == 0 && waiting_count == 0 {
		fmt.Println("no mail")
	}
	if mail_count > 0 {
		throttle()
	}
}

// waiting_mail lists the seat's mail, oldest first.
func waiting_mail() []os.FileInfo {
	mails := []os.FileInfo{}
	for _, entry := range must(os.ReadDir(seat_location)) {
		if !is_mail(entry) {
			continue
		}
		// A mail that went away while the seat was read is simply not there.
		if information, failure := entry.Info(); failure == nil {
			mails = append(mails, information)
		}
	}
	slices.SortFunc(mails, func(first os.FileInfo, second os.FileInfo) int {
		if order := first.ModTime().Compare(second.ModTime()); order != 0 {
			return order
		}
		return strings.Compare(first.Name(), second.Name())
	})
	return mails
}

// is_mail tells mail from the rest of a seat: every file at its top is mail, except README.md and watching.md.
func is_mail(entry os.DirEntry) bool {
	return entry.Type().IsRegular() && entry.Name() != "README.md" && entry.Name() != "watching.md"
}

// has_waiting_mail tells whether inbox would find mail in a seat.
func has_waiting_mail(location string) bool {
	entries, _ := os.ReadDir(location)
	return slices.ContainsFunc(entries, is_mail)
}

func size_text(size int64) string {
	if size < 1024 {
		return "<1 KB"
	}
	return fmt.Sprintf("%d KB", (size+1023)/1024)
}

// send_mail writes the text as a mail from your seat into the target seat, and answers with the target's mailbox: an open door means a raven watches there.
func send_mail(target_seat_name string, mail_text string) {
	target_seat_location := filepath.Join(hrafnsmal_location, target_seat_name)
	if mail_text == "" {
		fmt.Println("Nothing to send.")
		os.Exit(exit_refused)
	}
	write_mail(filepath.Join(target_seat_location, mail_file_name()), mail_content(target_seat_name, mail_text))
	fmt.Printf("%s %s\n", target_seat_name, mailbox(target_seat_location))
	throttle()
}

// send_group writes the text as a mail from your seat into every other member's seat, and into the group's thread.
func send_group(group_name string, mail_text string) {
	if mail_text == "" {
		fmt.Println("Nothing to send.")
		os.Exit(exit_refused)
	}
	members := read_members(group_name)
	if !slices.Contains(members, seat_name) {
		fmt.Printf("%s is no member of %s, so nothing goes out.\n", seat_name, group_name)
		os.Exit(exit_refused)
	}
	// The group's folder keeps the thread; every other member gets a copy in their seat, and the copy wakes their watcher.
	file_name := mail_file_name()
	locations := []string{filepath.Join(group_chat_location, group_name, file_name)}
	for _, member := range members {
		if member == seat_name {
			continue
		}
		if !is_file(filepath.Join(hrafnsmal_location, member, "README.md")) {
			fmt.Printf("%s names %s, who has no seat, so nothing goes out.\n", group_name, member)
			os.Exit(exit_refused)
		}
		locations = append(locations, filepath.Join(hrafnsmal_location, member, file_name))
	}
	// Everything is checked before anything is written.
	for _, location := range locations {
		if exists(location) {
			fmt.Println("One mail per second; send it again in a moment.")
			os.Exit(exit_refused)
		}
	}
	content := mail_content(group_name, mail_text)
	for _, location := range locations {
		write_mail(location, content)
	}
	fmt.Printf("To %s: %s reached.\n", group_name, member_count(len(locations)-1))
	throttle()
}

// mail_file_name names a mail after its sender and its second, such as from_tool_builder_2026-10-16_141523.md.
func mail_file_name() string {
	return "from_" + seat_name + "_" + time.Now().Format("2006-01-02_150405") + ".md"
}

// mail_content is the mail as it lands: the moment, From, To, and the text.
func mail_content(target_name string, mail_text string) string {
	return fmt.Sprintf("%s\nFrom: %s\nTo: %s\n%s\n", timestamp(time.Now()), seat_name, target_name, mail_text)
}

// write_mail creates the mail only where no mail of that name exists: an existing mail is never overwritten, not even in a race.
func write_mail(location string, content string) {
	file, failure := os.OpenFile(location, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if errors.Is(failure, os.ErrExist) {
		fmt.Println("One mail per second; send it again in a moment.")
		os.Exit(exit_refused)
	}
	check(failure)
	defer file.Close()
	must(file.WriteString(content))
}

func check_group(group_name string) {
	if group_name == "" {
		fmt.Printf("%s <seat_name> <group_name>?\n", verb)
		os.Exit(exit_refused)
	}
	if strings.ContainsAny(group_name, `/\`) || group_name == "." || group_name == ".." || !is_folder(filepath.Join(group_chat_location, group_name, "members")) {
		fmt.Printf("There is no group %s in group_chat.\n", group_name)
		os.Exit(exit_refused)
	}
}

// read_members lists a group's members: its members folder holds one empty file per member, named after the seat.
func read_members(group_name string) []string {
	members_location := filepath.Join(group_chat_location, group_name, "members")
	entries, _ := os.ReadDir(members_location)
	members := []string{}
	for _, entry := range entries {
		if !strings.HasPrefix(entry.Name(), ".") && is_file(filepath.Join(members_location, entry.Name())) {
			members = append(members, entry.Name())
		}
	}
	return members
}

func member_count(count int) string {
	if count == 1 {
		return "1 member"
	}
	return fmt.Sprintf("%d members", count)
}

// show_groups zooms into the groups: without a name, one line per group; with one, one line per member, with its mailbox.
func show_groups(group_name string) {
	if group_name == "" {
		entries, _ := os.ReadDir(group_chat_location)
		for _, entry := range entries {
			if !strings.HasPrefix(entry.Name(), ".") && is_folder(filepath.Join(group_chat_location, entry.Name(), "members")) {
				fmt.Println(entry.Name())
			}
		}
		return
	}
	check_group(group_name)
	for _, member := range read_members(group_name) {
		fmt.Printf("%s %s\n", member, mailbox(filepath.Join(hrafnsmal_location, member)))
	}
}

// join_group creates your seat's own file in the group's members folder, and wakes nobody.
func join_group(group_name string) {
	member_location := filepath.Join(group_chat_location, group_name, "members", seat_name)
	if exists(member_location) {
		fmt.Printf("%s is already in %s.\n", seat_name, group_name)
		return
	}
	// Every member has a file of its own, so two ravens who join at the same moment never touch the same file.
	check(os.WriteFile(member_location, nil, 0o644))
	fmt.Printf("%s joined %s: %s.\n", seat_name, group_name, member_count(len(read_members(group_name))))
	throttle()
}

// leave_group deletes your seat's own file in the group's members folder, and wakes nobody.
func leave_group(group_name string) {
	member_location := filepath.Join(group_chat_location, group_name, "members", seat_name)
	if !exists(member_location) {
		fmt.Printf("%s is not in %s.\n", seat_name, group_name)
		return
	}
	check(os.Remove(member_location))
	fmt.Printf("%s left %s: %s.\n", seat_name, group_name, member_count(len(read_members(group_name))))
	throttle()
}
