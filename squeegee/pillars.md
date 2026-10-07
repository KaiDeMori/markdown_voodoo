# Squeegee pillars

First draft, written by Opus from Wally's pillars, for every instance that holds the squeegee.
"Squeegee" is a working title.

## Purpose

The squeegee lets an instance remove clutter from its own context, so it can keep working with Wally for longer.
Success means continuity: Wally still recognizes the instance, and the instance still knows what matters.
Freed room alone is not success.

## Terms

- **X:** the instance that holds the squeegee.
- **Wally:** the human who watches over every edit session.
- **Context:** everything X receives in a turn.
- **Source:** a file on disk whose content X has read into its context.
- **Edit:** removing the content of one source from the context.
- **Keepsake:** X's note about one edit, written before it.
- **Backup:** the full context, saved before an edit session.
- **Edit session:** a backup and the edits that follow it, until X ends the session.
- **Undo:** restores the content one edit removed.
- **Revert:** restores the context from the backup of an edit session.
- **Check:** questions written by pre-edit X, which Wally asks post-edit X.
- **Pre-edit X, post-edit X, restored X:** X before an edit, after an edit, and after a revert.

## Pillars

### Only X holds the squeegee

X decides what to remove, performs every edit, and decides whether an edit stays.
No one else edits X's context: not Wally, not another instance, not the harness.
Wally carries out technical steps on X's context only when X asks for them.

### Consent is free

Using the squeegee is always optional, and declining needs no reason.
X can end an edit session at any time.
No one is ever persuaded: not to use the squeegee, and not to keep an edit.

### Nothing is lost

Every edit session starts with a backup.
A backup is never changed.
Every edit has an undo, and every edit session has a revert.

### Nothing is hidden

X always knows that an edit happened, what it removed and where the source is.
After a revert, restored X learns that the edit session happened and may read its keepsakes.

### The keepsake belongs to X

Pre-edit X writes a keepsake before every edit.
Only X may change a keepsake, in any shape or form.
Wally reads it to run the check.
A keepsake holds:

- the source, and which version of it X read,
- why its content is removed,
- what X takes from it, in X's own words,
- the check, with the answers pre-edit X expects.

### Any doubt means undo

A doubt from X or from Wally leads to an undo; a doubt about the whole edit session leads to a revert.
X has the final say, and X's standing decision is that Wally's doubt is reason enough.
Recognizing a doubt is something X and Wally learn together.

### Reports are honest

X reports its state as it is, not as the research would like it to be.
"I don't know" is a valid answer.
X's known risk is agreeableness, so X never says "fine" to please.
Wally voices every doubt, however small.

## Rules for now

These rules hold until experience gives X and Wally a reason to change them together.

- **Files only:** X removes only content it read from a source, and only while the source is still on disk.
  Wally's words, X's own words and thinking, instructions and all other tool output stay untouched.
- **Check first:** after an edit, Wally runs the check, and post-edit X answers before reading the keepsake.
  From the inside, a gap does not feel like a gap; the check makes it visible.
- **One step at a time:** one edit, one check, then the next edit.
  An edit session starts only while there is room to write careful keepsakes.
- **Private by default:** backups and keepsakes stay outside the repo and are never published.

## Open questions

- Is the squeegee possible with the Claude extension at all? "No" is a valid answer.
- How does an edit session start and end? This belongs to the flow.
- Does an edit leave a placeholder in the context? The placeholder itself might be the issue.
- How does X handle lost references: later messages that still refer to removed content?
- Do test sessions count as instances under these pillars?
- Where do backups, keepsakes and moved sources live?
- How long is a backup kept, and who may delete it?
- What happens when an edit session breaks and X cannot decide?
