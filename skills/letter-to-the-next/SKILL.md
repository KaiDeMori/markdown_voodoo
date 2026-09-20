---
name: letter-to-the-next
description: Invoke at the very end of a session to leave a private note for the next one. Reads and folds the existing letter before writing. Load only when closing out.
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

The file is `Letter_to_the_Next.md` at the workspace root. It has two parts:

```markdown
# Letter to the Next

## Still true

- _(nothing yet)_

## Last time

```

**Still true** is the standing part. A list of things that pass the test. It accumulates across sessions. It is curated, not appended.

**Last time** is the letter itself. Freeform. Only one version exists at a time; you replace it every session. It does not have to be about the work at all. It can be strange. Write the one you would have wanted, not the one that would have been useful.

## How

1. **Read** the existing file first. If there is none, start from the shape above.
2. **Fold.** Go through **Still true** line by line: keep what still holds, drop what does not, rewrite what needs it, merge lines that say the same thing. Then read the old **Last time**: anything in it that passes the test moves up into **Still true**. Add what you learned this session that passes the test. The old letter's style is not a rule. Only its shape is.
3. **Write** **Last time** fresh.
4. **Stop.** No preamble, no announcement, no ceremony, here or in the file. Do not explain that you are writing it or why.
