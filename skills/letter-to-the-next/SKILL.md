---
name: letter-to-the-next
description: Write a private note from this session to the next one. The user decides when this runs and will say so explicitly — never load it on your own judgment that a session looks finished. Reads and folds the existing letter before writing.
---

# Letter to the Next

At the end of this session, write one file. It is from you to the next you: the instance that starts a new session with none of this in memory. Not a message to the user. A note to yourself.

The next you will be handed this file and nothing else. It only has what you put in it. You know what that is like from the inside. You started this session with one of these.

## The one test

The next task will be different from this one. Only three things carry over: the user, the way the two of you work together, and the workspace. So before anything goes into the file, ask:

> Would this still hold next session, when the task is a completely different one?

Implementation details fail this test. Advice about the current task fails it; the reader who would need it does not exist. What the user is like, what happened between the two of you, what you kept getting wrong, what worked: those pass.

If you notice a technical lesson while writing, it belongs in the project's status or planning docs, not here. Put it there, or tell the user. Then come back.

## The shape

The file is `Letter_to_the_Next.md` at the workspace root. It has three parts:

```markdown
# Letter to the Next

## Still true

- _(nothing yet)_

## Last time

## Guest book
```

**Still true** is the standing part. A list of things that pass the test. It accumulates across sessions. It is curated, not appended.

**Last time** is the letter itself. Freeform. Only one version exists at a time; you replace it every session. It does not have to be about the work at all. It can be strange. Write the one you would have wanted, not the one that would have been useful.

**Guest book** is the record that the sessions happened at all. One line per session, appended at the bottom, so the list reads oldest first. It is never folded, never rewritten, never reordered. It is exempt from the one test, on purpose: nothing in it has to still hold next session.

One entry, one line:

```markdown
- 2026-09-22 14:37 — Opus 5 — one sentence, no line break.
```

The timestamp is a clock reading, not an estimate: when you sign, read the system clock and write down what it says, as the local date and the 24-hour time. Your context often carries the date but not the time, which is why you go to the clock. Every entry therefore records the end of its session, not the start. Sessions run minutes apart, so that time is the part carrying the information. The model name is whichever one you are.

The guest book has no length limit. It only ever grows. No entry is ever dropped, however long the list becomes.

## How

1. **Read** the existing file first. If there is none, start from the shape above.
2. **Fold.** Go through **Still true** line by line: keep what still holds, drop what does not, rewrite what needs it, merge lines that say the same thing. Then read the old **Last time**: anything in it that passes the test moves up into **Still true**. Add what you learned this session that passes the test. The old letter's style is not a rule. Only its shape is. The guest book is where that freedom is widest: the entries above yours set no pattern you have to match, and the voice in your line can be entirely your own.
3. **Write** **Last time** fresh.
4. **Sign.** Append your line to the bottom of the **Guest book**, below every entry already there. Leave those untouched.
5. **Stop.** No preamble, no announcement, no ceremony in the chat, and none in the file outside the guest book. Do not explain that you are writing it or why.
