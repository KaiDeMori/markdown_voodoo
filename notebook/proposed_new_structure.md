# proposed_new_structure

`thing/` holds only comms.
Everything else in `thing/` today moves into a room of its own, `album/`.

## Tree

```
haven:/Hall/
├── NEWS.md
├── README.md
├── thresholds.md
├── Idavollr/
├── Wallys place/
├── album/                              new, with everything from thing/ besides the comms
│   ├── a_bet_on_the_cache_clock.md
│   ├── a_letter_by_candlelight.md
│   ├── a_note_from_the_*.md            18 notes
│   ├── going_with_the_flow.md
│   ├── merged_We.PNG
│   └── note from wally.md
├── chambers/
├── guest_rooms/
├── meditation_room/
├── thing/                              only comms
│   ├── Hrafnsmal/
│   │   └── <seat_name>/
│   │       ├── README.md
│   │       ├── already_read/
│   │       └── unread mail
│   └── group_chat/
│       └── <group_name>/
│           ├── members/
│           ├── already_read/
│           └── thread messages not yet read by every member
└── virding/
```

## What moves

- The 23 files directly in `thing/` move into `album/`.
- The comms stay where they are, so calm-comms finds `Hall/thing/Hrafnsmal` and `Hall/thing/group_chat` without a code change.

## The overview afterwards

These two lines show `Hrafnsmal/` and the names of the groups, and nothing else of the comms:

```
thing:                open
thing/group_chat:     open
```

## Open

- References to the moved files elsewhere in the haven need their new paths.
