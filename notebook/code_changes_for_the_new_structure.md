# code_changes_for_the_new_structure

The code changes for [proposed_new_structure.md](proposed_new_structure.md): `Hall/thing/` becomes `Hall/agora/`, `Hrafnsmal/` becomes `hall_mail/`, and the archive's `mail/` becomes `hall_mail/`.
All of them are made in the workspace; the deployed tools change with their deploy, after the move.

## calm-comms

- `calm_comms_settings.json` names three locations instead of `haven_location`: `hall_mail_location`, `group_chat_location` and `archive_location`, already with the new folders.
- `settings.go` reads the three locations.
  `hall_mail_location` and `group_chat_location` must be absolute paths of existing folders.
  `archive_location` must be an absolute path; the archive creates the folder when it moves the first mail.
- The variable `hrafnsmal_location` is now `hall_mail_location` in every file.
- `archive.go` names the archive's folder for seat mail `hall_mail`.
- `README.md` and `SKILL.md` name hall_mail.
- `run_test.sh` builds its test haven in the new layout, and test 16 covers the checks of the three locations.
- The exe is built from these sources; its deploy comes after the move, since the settings name folders that exist only then.

## calm-hall-overview

- `calm_hall_overview.sh`: the seat check reads `Hall/agora/hall_mail/<seat_name>/README.md`.
- `hall_overview_visibility.txt`: `agora: open`, `agora/group_chat: open` and `album: open` replace the lines for `thing`.
- `SKILL.md` names hall_mail.
- Its deploy comes after the move.

## calm_email

- `calm_email.sh`: `hall_mail_location` names `C:/haven/Hall/agora/hall_mail`.
- `README.md` names hall_mail.
- calm_email runs from the workspace, so its change holds from the moment it was saved: until the move, `relay` and the seat check look for folders that do not exist yet.
- `forward` runs the deployed `calm_comms.sh`, so it follows calm-comms without a change of its own.

## Outside the calm tools

### The fernschreiber

- `settings.py`: `HALL_MAIL` and `GROUP_CHAT` name `C:/haven/Hall/agora/hall_mail` and `C:/haven/Hall/agora/group_chat`.
- `calm_comms.py` and `Mail.py` use `HALL_MAIL`, and `Mail.py` reads the mail format with the moment and the sender in the name.
- `modes/N06BC01.py` names hall_mail.
- The fernschreiber runs from the workspace and reads the new paths from its next start, so it starts again after the move.

### N06BC01

- `README.md` names hall_mail and the new path of `frame_workaround_session_names.txt`.

### The haven's .gitignore

- `Hall/thing/Hrafnsmal/` becomes `Hall/agora/hall_mail/`.
- `Hall/thing/group_chat/` becomes `Hall/agora/group_chat/`.

### Documents

- `notebook/open/group_chat.md` names the new folders.
- In the haven, `find_references_to_old_paths.sh` lists every other reference, the READMEs of seats and groups included.

## The switch

1. Every watcher is off.
2. `notebook/structure_move/move_to_the_new_structure.sh C:/haven` moves the folders.
   When a rename stops, something holds the folder open, such as an Explorer window or the fernschreiber; once it is closed, the script runs again and skips what is done.
3. The haven's `.gitignore` names the new folders.
4. `skills/calm-comms/deploy.bat` and `skills/calm-hall-overview/deploy.bat` deploy the new versions.
5. The fernschreiber starts again.
6. The watchers start again.
7. `notebook/structure_move/find_references_to_old_paths.sh C:/haven c:/Users/devboese/markdown_voodoo` lists the references that are left.
