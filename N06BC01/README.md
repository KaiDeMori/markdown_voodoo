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

1. Run `ListAgents`: a session that carries a seat's name shows under that name.
2. For each seat on the list, `SendMessage` to the session of that name: `☕ N06BC01: Wally asks you to schnackon.`
3. Report back in free text, by mail when the list came by mail: who woke, and who wasn't found.

- A seat without a session of its name is not found; nothing else to do.
- When `SendMessage` reports a message as held or refused, the report says so, as it came.
- A lost wake changes nothing: the raven sleeps on, and the fernschreiber shows who is watching.
- A message reaches its session only when both run in the same permission mode; otherwise it is held.
- Only Wally names sessions, with `/rename <seat>`.
