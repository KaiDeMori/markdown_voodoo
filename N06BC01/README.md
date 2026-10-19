# N06BC01

The hallmaster's program for waking ravens. ☕
N06BC01 is caffeine's ATC code; both zeros are zeros.
It is not a skill on purpose: only the hallmaster needs it, so no other raven finds it in a skill list.

## For the hallmaster

Your job: wake the ravens on a list, and say how it went.
Your seat in Hrafnsmal is `hallmaster`.

A wake mail looks like this:

```
☕ N06BC01: please wake these ravens and ask them to schnackon
tool_builder
otis_builder
```

The first line is always the same; then one seat per line, nothing else.
Until the fernschreiber sends it, Wally hands you the list directly.

1. Run `ListAgents`: it lists every other session on this machine.
2. `SendMessage` the same wake message to every session in that list, with the seats from the mail:

   ```
   ☕ N06BC01: Wally asks these seats to schnackon: tool_builder, otis_builder.
   If your seat is on the list: schnackon, then read your name in the first line of ListAgents.
   If that name isn't your seat, show Wally a fenced code block with /rename <your seat>.
   If your seat isn't on the list, or you have none: nothing to do.
   ```

3. Report back in free text, by mail when the list came by mail: the messages that were held or refused, and from `calm-comms overview`, who on the list is watching.

- Session names change with every restart, but every raven knows its seat from its own window, so the wake needs no names.
- When `SendMessage` reports a message as held or refused, the report says so, as it came.
- A lost wake changes nothing: the raven sleeps on, and the overview shows it.
- A message reaches its session only when both run in the same permission mode; otherwise it is held.
- Only Wally can run `/rename`; a raven with the wrong name shows Wally the line to paste.
