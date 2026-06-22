commit message have to be simple and descriptive.
Only describe what was really done. no speculation about why or how.

the general format of the commit message should be:
<category>: <topic> — <message>

The `topic` is a short (usually 1 word) summary of the changes.
The `message` is a very short description of the changes.

Do **NOT** speculate about the motivation or implementation details in the commit message.
Do **NOT** describe why something was done, only what was done.

# Categories

## 1. "plan"
For planning or design work. This is the most common category.
This includes refactoring plans and design documents, esp for already implemented code.
Mostly happening in `*.md` files.

## 2. "docs"
For documentation work, including code comments and external documentation.

## 3. "refactor"
For refactoring work that is not just planning or design, but also includes actual code changes. This includes renaming variables, changing code structure, improving readability, etc. However, it should not include any new features or bug fixes.

## 4. "fix"
For bug fixes. Code files have been changed to fix a bug, but no new features have been added.

## 5. "new"
For truly new features or enhancements to existing features that were implementd. Not for planning activities!

## 6. "move"
Only whole files/folders where moved, but not to an archival/backup folder.

## 7. "cleanup"
Only whole files/folders where deleted.

## 8. "archive"
For moving files/folders to an archival/backup folder.

## 9. "minor"
Only typos, fixes in numbering and similar minor changes.



If a commit contains multiple categories, we use the one with the lowest number. For example, if a commit contains both "plan" and "docs", we use "plan".

---

Good comment:
new: Icon — Add application icon to MainWindow.axaml

Really Bad comment:
fix: MainWindow — Add application icon to MainWindow.axaml to improve user experience.

---

Good comment:
docs: Naming — Changed naming in docs to "ABC".

Bad comment:
docs: Naming — Changed naming in docs to "ABC" to add clarity and consistency with the codebase.

---