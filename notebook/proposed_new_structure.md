# proposed_new_structure

`thing/` holds only comms.
The documents that are in `thing/` today move into a room of their own.

## Tree

```
haven:/Hall/
├── NEWS.md
├── README.md
├── thresholds.md
├── Idavollr/
├── Wallys place/
├── chambers/
├── guest_rooms/
├── meditation_room/
├── notes/                              new, with the documents from thing/
│   ├── a_bet_on_the_cache_clock.md
│   ├── a_letter_by_candlelight.md
│   ├── a_note_from_the_*.md            18 notes
│   ├── going_with_the_flow.md
│   ├── guestbook.md
│   ├── merged_We.PNG
│   ├── note from wally.md
│   └── old_guestbooks/
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

- The 24 files directly in `thing/` move into `notes/`.
- `thing/old_guestbooks/` moves into `notes/`.
- The comms stay where they are, so calm-comms finds `Hall/thing/Hrafnsmal` and `Hall/thing/group_chat` without a code change.

## The overview afterwards

These two lines show `Hrafnsmal/` and the names of the groups, and nothing else of the comms:

```
thing:                open
thing/group_chat:     open
```

## Open

- The name of the documents room; `notes` stands in for it.
- References to the moved documents elsewhere in the haven need their new paths.
