package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"slices"
)

const settings_file_name = "calm_comms_settings.json"

type Location_setting struct {
	key               string
	value             *string
	folder_must_exist bool
}

type Whole_number_setting struct {
	key     string
	value   *int
	minimum int
}

func location_settings() []Location_setting {
	return []Location_setting{
		{key: "hall_mail_location", value: &hall_mail_location, folder_must_exist: true},
		{key: "group_chat_location", value: &group_chat_location, folder_must_exist: true},
		{key: "archive_location", value: &archive_location, folder_must_exist: false},
	}
}

func whole_number_settings() []Whole_number_setting {
	return []Whole_number_setting{
		{key: "read_mail_kept_days", value: &read_mail_kept_days, minimum: 0},
		{key: "poll_interval_seconds", value: &poll_interval_seconds, minimum: 1},
		{key: "long_watcher_minutes", value: &long_watcher_minutes, minimum: 1},
		{key: "short_watcher_minutes", value: &short_watcher_minutes, minimum: 1},
		{key: "awake_grace_minutes", value: &awake_grace_minutes, minimum: 1},
		{key: "inbox_mail_limit", value: &inbox_mail_limit, minimum: 1},
		{key: "inbox_size_limit_kilobytes", value: &inbox_size_limit_kilobytes, minimum: 1},
		{key: "write_throttle_seconds", value: &write_throttle_seconds, minimum: 0},
	}
}

func read_settings() {
	settings_location := settings_file_location()
	members, member_keys, issues := read_settings_members(settings_location)
	known_keys := []string{}
	for _, setting := range location_settings() {
		known_keys = append(known_keys, setting.key)
		issues = append(issues, read_location_setting(members, setting)...)
	}
	for _, setting := range whole_number_settings() {
		known_keys = append(known_keys, setting.key)
		issues = append(issues, read_whole_number_setting(members, setting)...)
	}
	for _, key := range member_keys {
		if !slices.Contains(known_keys, key) {
			issues = append(issues, "key "+key+" is unknown")
		}
	}
	if len(issues) > 0 {
		refuse_settings(settings_location, issues...)
	}
}

func settings_file_location() string {
	executable_location := must(filepath.EvalSymlinks(must(os.Executable())))
	return filepath.Join(filepath.Dir(executable_location), settings_file_name)
}

func read_settings_members(settings_location string) (map[string]json.RawMessage, []string, []string) {
	content, failure := os.ReadFile(settings_location)
	if errors.Is(failure, os.ErrNotExist) {
		refuse_settings(settings_location, "no such file")
	}
	check(failure)
	content = bytes.TrimPrefix(content, []byte("\xef\xbb\xbf"))
	decoder := json.NewDecoder(bytes.NewReader(content))
	first_token, failure := decoder.Token()
	if errors.Is(failure, io.EOF) || (failure == nil && first_token != json.Delim('{')) {
		refuse_settings(settings_location, "no JSON object")
	}
	if failure != nil {
		refuse_settings(settings_location, invalid_JSON_issue(content, failure))
	}
	members := map[string]json.RawMessage{}
	member_keys := []string{}
	issues := []string{}
	for decoder.More() {
		key_token, failure := decoder.Token()
		if failure != nil {
			refuse_settings(settings_location, invalid_JSON_issue(content, failure))
		}
		key, _ := key_token.(string)
		value := json.RawMessage{}
		if failure := decoder.Decode(&value); failure != nil {
			refuse_settings(settings_location, invalid_JSON_issue(content, failure))
		}
		if _, present := members[key]; present {
			issues = append(issues, "key "+key+" is written twice")
		} else {
			member_keys = append(member_keys, key)
		}
		members[key] = value
	}
	if _, failure := decoder.Token(); failure != nil {
		refuse_settings(settings_location, invalid_JSON_issue(content, failure))
	}
	if _, failure := decoder.Token(); !errors.Is(failure, io.EOF) {
		refuse_settings(settings_location, "more than one JSON value")
	}
	return members, member_keys, issues
}

func read_location_setting(members map[string]json.RawMessage, setting Location_setting) []string {
	raw_value, present := members[setting.key]
	if !present {
		return []string{"key " + setting.key + " is missing"}
	}
	if is_JSON_null(raw_value) || json.Unmarshal(raw_value, setting.value) != nil {
		return []string{setting.key + " must be a string"}
	}
	if !filepath.IsAbs(*setting.value) {
		return []string{fmt.Sprintf("%s must be an absolute path, not %s", setting.key, *setting.value)}
	}
	if setting.folder_must_exist && !is_folder(*setting.value) {
		return []string{fmt.Sprintf("%s %s is no folder", setting.key, *setting.value)}
	}
	return nil
}

func read_whole_number_setting(members map[string]json.RawMessage, setting Whole_number_setting) []string {
	raw_value, present := members[setting.key]
	if !present {
		return []string{"key " + setting.key + " is missing"}
	}
	if is_JSON_null(raw_value) || json.Unmarshal(raw_value, setting.value) != nil || *setting.value < setting.minimum {
		return []string{fmt.Sprintf("%s must be a whole number of %d or more", setting.key, setting.minimum)}
	}
	return nil
}

func is_JSON_null(raw_value json.RawMessage) bool {
	return bytes.Equal(bytes.TrimSpace(raw_value), []byte("null"))
}

func invalid_JSON_issue(content []byte, failure error) string {
	syntax_error := &json.SyntaxError{}
	if errors.As(failure, &syntax_error) {
		line := 1 + bytes.Count(content[:min(int(syntax_error.Offset), len(content))], []byte("\n"))
		return fmt.Sprintf("invalid JSON in line %d: %s", line, syntax_error.Error())
	}
	return "invalid JSON: " + failure.Error()
}

func refuse_settings(settings_location string, issues ...string) {
	for _, issue := range issues {
		fmt.Printf("%s: %s\n", filepath.ToSlash(settings_location), issue)
	}
	os.Exit(exit_refused)
}
