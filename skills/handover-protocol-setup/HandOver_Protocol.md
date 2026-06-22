# HandOver Protocol (HOP)

How work is handed from one session to the next in this long-running, multi-session project.
Everything needed to resume lives in the workspace as files — the baton and the planning docs —
never only in an agent's memory. This file is **stable**: it explains the mechanism. The moving
part it describes, `Status.md`, is **dynamic** and lives separately, so that if it ever gets
mangled the protocol itself is never lost.

## The baton: `Status.md`

`Status.md` (repo root) is the **hand-over baton**. It is deliberately *neither* a "what's
done" log *nor* a "what's next" plan — it sits **exactly in between**: where we are *right
now*, and the single next step from here. Keep it short.

A fresh `Status.md` starts from this shape:

```markdown
# Status — the hand-over baton

> How to use and update this file: see `HandOver_Protocol.md`.

## Where we are right now

- _(Starting point. Always reflects the present moment, not a history.)_

## Next step

- _(The single next step from here.)_

## Open threads (not blocking)

- _(none yet)_
```

## What a fresh session does

1. **Read** `Status.md` (after `CLAUDE.md`).
2. **Adjust** it — fold the old "Next step" into "Where we are", then write the new next step
   — so the baton always reflects the present moment.
3. **Continue** the work from there.

## When to update `Status.md`

At the **end of a milestone** or **on user request** — not continuously (it is a baton, not a
diary).

## Keep it lean

`Status.md` carries only the present moment. Anything explanatory, structural, or long-lived
belongs elsewhere — the detailed thinking lives in the project's planning docs, not in the
baton. That separation is the point: the dynamic file stays small and disposable; the protocol
stays safe here.
