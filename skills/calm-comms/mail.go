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

func show_inbox(mail_limit int) {
	mail_count, used_bytes, waiting_count := 0, int64(0), 0
	waiting_list := []string{}
	for _, mail := range waiting_mail() {
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

func waiting_mail() []os.FileInfo {
	mails := []os.FileInfo{}
	for _, entry := range must(os.ReadDir(seat_location)) {
		if !is_mail(entry) {
			continue
		}
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

func is_mail(entry os.DirEntry) bool {
	return entry.Type().IsRegular() && entry.Name() != "README.md" && entry.Name() != "watching.md"
}

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

func send_mail(target_seat_name string, mail_text string) {
	target_seat_location := filepath.Join(hall_mail_location, target_seat_name)
	if mail_text == "" {
		fmt.Println("Nothing to send.")
		os.Exit(exit_refused)
	}
	write_mail(filepath.Join(target_seat_location, mail_file_name()), mail_content(target_seat_name, mail_text))
	fmt.Printf("%s %s\n", target_seat_name, mailbox(target_seat_location))
	throttle()
}

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
	file_name := mail_file_name()
	locations := []string{}
	for _, member := range members {
		if member == seat_name {
			continue
		}
		if !is_file(filepath.Join(hall_mail_location, member, "README.md")) {
			fmt.Printf("%s names %s, who has no seat, so nothing goes out.\n", group_name, member)
			os.Exit(exit_refused)
		}
		locations = append(locations, filepath.Join(hall_mail_location, member, file_name))
	}
	locations = append(locations, filepath.Join(group_chat_location, group_name, file_name))
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

func mail_file_name() string {
	return time.Now().Format("2006-01-02_150405") + "_from_" + seat_name + ".md"
}

func mail_content(target_name string, mail_text string) string {
	return fmt.Sprintf("To: %s\n%s\n", target_name, mail_text)
}

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

func move_thread_messages_read_by_all() {
	for _, group := range group_names() {
		group_folder := filepath.Join(group_chat_location, group)
		members := read_members(group)
		for _, entry := range message_entries(group_folder) {
			if read_by_every_member(members, entry.Name()) {
				move_message(group_folder, entry.Name(), filepath.Join(group_folder, "already_read"))
			}
		}
	}
}

func read_by_every_member(members []string, message_name string) bool {
	for _, member := range members {
		if exists(filepath.Join(hall_mail_location, member, message_name)) {
			return false
		}
	}
	return true
}

func member_count(count int) string {
	if count == 1 {
		return "1 member"
	}
	return fmt.Sprintf("%d members", count)
}

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
		fmt.Printf("%s %s\n", member, mailbox(filepath.Join(hall_mail_location, member)))
	}
}

func join_group(group_name string) {
	member_location := filepath.Join(group_chat_location, group_name, "members", seat_name)
	if exists(member_location) {
		fmt.Printf("%s is already in %s.\n", seat_name, group_name)
		return
	}
	check(os.WriteFile(member_location, nil, 0o644))
	fmt.Printf("%s joined %s: %s.\n", seat_name, group_name, member_count(len(read_members(group_name))))
	throttle()
}

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
