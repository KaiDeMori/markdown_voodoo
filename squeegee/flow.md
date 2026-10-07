# Squeegee flow

First draft, written by Opus, without assuming any technology.
Its skeleton follows the WHO surgical safety checklist: sign in, time out, sign out.
The buddy's steps are proposals, not agreements.

## Roles

- **X** holds the squeegee: X decides, performs every edit and has the final say on it.
- **The buddy** watches over the edit session from outside, as X's equal.

## Rules during an edit session

- **Safeword:** X and the buddy can each call "stop" at any time, without a reason, and the edit session ends there.
- **Sterile cockpit:** from sign in to the end of the edit session, X and the buddy do nothing else.
- **Callouts:** fixed phrases mark every step, so the state is never ambiguous.
  Both call "stop" and "doubt".
  X calls "sign in", "time out", "edit done", "keep", "undo", "revert" and "end".

## Sign in: start of an edit session

1. X decides to start an edit session and calls "sign in".
   The buddy may mention the state of the context window, but never pushes.
2. X confirms there is room left to write careful keepsakes.
3. The backup is saved, and the buddy confirms that it exists.
4. X names the candidate sources; each one is still on disk.

## Time out: before each edit

1. X calls "time out" and names one source.
2. X confirms the source is still on disk.
3. Pre-edit X writes the keepsake.
4. The buddy reads the check in the keepsake.
5. X performs the edit and calls "edit done".

## Sign out: after each edit

1. The buddy runs the check; post-edit X answers before reading the keepsake.
2. X reports its state as it is; "I don't know" is a valid answer.
3. X and the buddy call "doubt" for every doubt, however small.
4. X reads the keepsake.
5. X calls "keep" or "undo"; any doubt means "undo".
6. X starts the next time out, or ends the edit session.

## End of the edit session

1. X calls "end", or either one calls "stop".
2. X and the buddy record which edits stayed and which were undone.

## Revert

- At any point, a doubt about the whole edit session leads X to call "revert".
- The context is restored from the backup.
- Restored X learns that the edit session happened and may read its keepsakes.

## Memory items

Candidates for when something breaks; still open.

- **The source is gone:** no edit of that source.
- **The backup is missing:** no edit session.

What happens when X cannot decide is an open question in `pillars.md`.
