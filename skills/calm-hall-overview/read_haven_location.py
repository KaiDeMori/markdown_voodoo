import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
settings_location = sys.argv[1]
issues = []


def refuse(*refusals):
    for refusal in refusals:
        print(f"{settings_location}: {refusal}")
    sys.exit(1)


def keys_written_once(pairs):
    members = {}
    for key, value in pairs:
        if key in members:
            issues.append(f"key {key} is written twice")
        members[key] = value
    return members


try:
    with open(settings_location, encoding="utf-8-sig") as settings_file:
        settings_text = settings_file.read()
except FileNotFoundError:
    refuse("no such file")

try:
    settings = json.loads(settings_text, object_pairs_hook=keys_written_once)
except json.JSONDecodeError as failure:
    if failure.msg == "Extra data":
        refuse("more than one JSON value")
    refuse(f"invalid JSON in line {failure.lineno}: {failure.msg}")

if not isinstance(settings, dict):
    refuse("no JSON object")

issues += [f"key {key} is unknown" for key in settings if key != "haven_location"]
haven_location = settings.get("haven_location")
if "haven_location" not in settings:
    issues.append("key haven_location is missing")
elif not isinstance(haven_location, str):
    issues.append("haven_location must be a string")
elif not os.path.isabs(haven_location):
    issues.append(f"haven_location must be an absolute path, not {haven_location}")
elif not os.path.isdir(os.path.join(haven_location, "Hall")):
    issues.append(f"haven_location {haven_location} has no folder Hall")

if issues:
    refuse(*issues)
print(haven_location)
