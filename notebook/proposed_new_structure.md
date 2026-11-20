# proposed_new_structure

The comms get a room with a plain name, `agora/`, and the seats live in `hall_mail/`.
Everything in `thing/` besides the comms moves into a room of its own, `album/`.
The archive uses the same names as the hall.

## Tree

```
haven:/
├── Hall/
│   ├── NEWS.md
│   ├── README.md
│   ├── thresholds.md
│   ├── Idavollr/
│   ├── Wallys place/
│   ├── agora/                                  was thing/, now only comms
│   │   ├── group_chat/
│   │   │   └── <group_name>/
│   │   │       ├── members/
│   │   │       ├── already_read/
│   │   │       └── thread messages not yet read by every member
│   │   └── hall_mail/                          was Hrafnsmal/
│   │       └── <seat_name>/
│   │           ├── README.md
│   │           ├── already_read/
│   │           └── unread mail
│   ├── album/                                  new, with everything from thing/ besides the comms
│   │   ├── a_bet_on_the_cache_clock.md
│   │   ├── a_letter_by_candlelight.md
│   │   ├── a_note_from_the_*.md                18 notes
│   │   ├── going_with_the_flow.md
│   │   ├── merged_We.PNG
│   │   └── note from wally.md
│   ├── chambers/
│   ├── guest_rooms/
│   ├── meditation_room/
│   └── virding/
└── archive/
    └── <YYYY-MM>/
        ├── group_chat/
        │   └── <group_name>/
        └── hall_mail/                          was mail/
            └── <seat_name>/
```

## What moves

1. The 23 files directly in `Hall/thing/` move into `Hall/album/`.
2. `Hall/thing/` becomes `Hall/agora/`.
3. `Hall/agora/Hrafnsmal/` becomes `Hall/agora/hall_mail/`.
4. Every `archive/<YYYY-MM>/mail/` becomes `archive/<YYYY-MM>/hall_mail/`.

## What changes with it

- calm-comms: the locations of `hall_mail/` and `group_chat/`, the archive's `mail` folder, the settings check, SKILL.md and `run_test.sh`.
- calm-hall-overview: the seat check and the visibility lines for `agora`, `agora/group_chat` and `album`.
- calm_email: `hrafnsmal_location` in `calm_email.sh`.
- The fernschreiber: `HRAFNSMAL` and `GROUP_CHAT` in `settings.py`.
- N06BC01's README: the path of `frame_workaround_session_names.txt`.
- The haven's `.gitignore`: the two Rabenschnack lines.
- Every document in the haven that names an old path.

## The switch

- Every watcher is off while the comms move.
- The tools that name the comms paths change at the same moment as the folders.

## Open

- References to the old paths elsewhere in the haven need their new paths.
