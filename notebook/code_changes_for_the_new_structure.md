# code_changes_for_the_new_structure

The code changes for [proposed_new_structure.md](proposed_new_structure.md): `Hall/thing/` becomes `Hall/agora/`, `Hrafnsmal/` becomes `hall_mail/`, and the archive's `mail/` becomes `hall_mail/`.

## calm-comms

- `calm_comms_settings.json` names three locations instead of `haven_location`: `hall_mail_location`, `group_chat_location` and `archive_location`.
- Before the switch, they name today's folders: `C:/haven/Hall/thing/Hrafnsmal`, `C:/haven/Hall/thing/group_chat` and `C:/haven/archive`.
- At the switch, the first two become `C:/haven/Hall/agora/hall_mail` and `C:/haven/Hall/agora/group_chat`.
- `settings.go` reads the three locations.
  `hall_mail_location` and `group_chat_location` must be absolute paths of existing folders.
  `archive_location` must be an absolute path; the archive creates the folder when it moves the first mail.
- `settings.go` no longer builds locations from `haven_location`, and its check for `Hall/thing/Hrafnsmal` is deleted.
- `archive.go` names the archive's folder for seat mail `hall_mail` instead of `mail`.
- The variable `hrafnsmal_location` becomes `hall_mail_location` in every file.
- `README.md`: "names the haven" becomes "names the folders".
- `run_test.sh`: the test haven uses `Hall/agora/hall_mail` and `Hall/agora/group_chat`, and its settings file the three locations.
  Test 15 expects `archive/<YYYY-MM>/hall_mail/`, and test 16 covers the checks of the three locations.
- `SKILL.md`: "your own seat's folder name in Hrafnsmal" becomes "in hall_mail" at the switch, so the ravens reload it once.

## calm-hall-overview

- `calm_hall_overview.sh`: the seat check reads `Hall/agora/hall_mail/<seat_name>/README.md` instead of `Hall/thing/Hrafnsmal/<seat_name>/README.md`.
- `hall_overview_visibility.txt`: `agora: open` and `agora/group_chat: open` replace the lines for `thing`, and `album` gets a line of its own.
- `SKILL.md`: "your own seat's folder name in Hrafnsmal" becomes "in hall_mail".
- All three change at the switch, right after the move.

## calm_email

- `calm_email.sh`: `hrafnsmal_location` becomes `hall_mail_location`, with the value `C:/haven/Hall/agora/hall_mail`.
- `README.md`: "Your seat in Hrafnsmal is `postmaster`" becomes "Your seat in hall_mail is `postmaster`".
- `forward` runs the deployed `calm_comms.sh`, so it follows calm-comms without a change of its own.
- Both changes happen at the switch, right after the move.

## Outside the calm tools

### The fernschreiber

- `settings.py`: `HRAFNSMAL` and `GROUP_CHAT` name `C:/haven/Hall/agora/hall_mail` and `C:/haven/Hall/agora/group_chat`, and `HRAFNSMAL` becomes `HALL_MAIL`.
- `Mail.py`: the two docstrings say "hall_mail format" instead of "Hrafnsmal format".
- `modes/N06BC01.py`: "a seat not found in Hrafnsmal" becomes "a seat not found in hall_mail".

### N06BC01

- `README.md`: "Your seat in Hrafnsmal is `hallmaster`" becomes "Your seat in hall_mail is `hallmaster`".
- `README.md`: the path of `frame_workaround_session_names.txt` becomes `haven:/Hall/agora/hall_mail/frame_workaround_session_names.txt`.

### The haven's .gitignore

- `Hall/thing/Hrafnsmal/` becomes `Hall/agora/hall_mail/`.
- `Hall/thing/group_chat/` becomes `Hall/agora/group_chat/`.

### Documents

- `notebook/open/group_chat.md` names `Hall/thing/group_chat/` and Hrafnsmal.
- In the haven, `find_references_to_old_paths.sh` lists every other reference.

## The switch

1. Before the switch: calm-comms with the three locations is built, tested and deployed, still naming today's folders.
2. Every watcher is off.
3. `notebook/structure_move/move_to_the_new_structure.sh C:/haven` moves the folders.
4. calm-comms: its settings name the new folders, its SKILL.md says hall_mail, and `deploy.bat` deploys both.
5. calm-hall-overview, calm_email, the fernschreiber, N06BC01's README and the haven's `.gitignore` change, and calm-hall-overview is deployed.
6. The watchers start again.
7. `notebook/structure_move/find_references_to_old_paths.sh C:/haven c:/Users/devboese/markdown_voodoo` lists the references that are left.

## Open

- The word for `album` in `hall_overview_visibility.txt`.
