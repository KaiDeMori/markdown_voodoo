commit message have to be simple and descriptive.
Only describe what was really done. no speculation about why or how.

the general format of the commit message should be:
<category>: <topic> — <message>
exceptions are marked as `(<category> only)`

The `topic` is a short (usually 1 word, maximum of 3 words) summary of the changes.
The `message` is a very short description of the changes.

Do **NOT** speculate about the motivation or implementation details in the commit message.
Do **NOT** describe why something was done, only what was done.

The Categories are ordered. start at the top and take the first one that matches the current commit.
If multiple categories apply, each one has to be present.

# Categories

## 1. "minor" (<category> only)
Minor change, mostly typos and formatting details. <category> only! text is just "typo" and nothing else.

## 3. "archive" (<category> only)
Only whole files/folders were moved to an archival/backup folder.

## 4. "move" (<category> only)
Only whole files/folders were moved (but not to an archival/backup folder)

## 5. "cleanup" (<category> only)
Only whole files/folders were deleted. 

## 6. "plan"
For planning or design work. When the content of "*.md" files was changed that have the name "task" or "plan" in it.

## 2. "docs"
For documentation work, including code comments and external documentation. No actual code was changed.

## 7. "fix"
For bug fixes. Code files have been changed to fix a bug, but no new features have been added.

## 8. "new"
For truly new features or enhancements to existing features that were implemented.

---

Good comment:
new: Icon — Add application icon to MainWindow.axaml

Really Bad comment (contains duplication and speculation):
fix: MainWindow — Add application icon to MainWindow.axaml to improve user experience.

---

Good comment:
docs: Naming — Semantic change from "Alphabet" to "ABC".

Bad comment (less specific, contains duplication, speculation):
docs: Naming — Changed naming in docs to "ABC" to add clarity and consistency with the codebase.

---

Good comment:
move

Bad comment (not conforming to `(<category> only)` rule):
move: documentation file foobar.md was moved

---
