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
   If you have a seat: append one line to haven:/Hall/thing/Hrafnsmal/sessions.txt: your seat, a space, and your name as the first line of ListAgents shows it, ref included.
   If your seat is on the list: schnackon too.
   If you have no seat: nothing to do.
   ```

3. Report back in free text, by mail when the list came by mail: the messages that were held or refused, and from `calm-comms overview`, who on the list is watching.

- Session names change with every restart, but every raven knows its seat from its own window, so the broadcast needs no names.
- `sessions.txt` is only ever appended to, so ravens waking at the same moment never overwrite each other; the last line of a seat wins.
- When `SendMessage` reports a message as held or refused, the report says so, as it came.
- A lost wake changes nothing: the raven sleeps on, and the overview shows it.
- A message reaches its session only when both run in the same permission mode; otherwise it is held.

## Waking a single seat

Between two restarts, a seat's last line in `haven:/Hall/thing/Hrafnsmal/sessions.txt` names its session, for example `tool_builder markdown-voodoo-a2 [3f99aa]`.
`SendMessage` to that name, with its ref when two sessions share the name, and the wake message with that one seat.
A name that `ListAgents` no longer shows means a restart came in between: the broadcast finds the raven again.
