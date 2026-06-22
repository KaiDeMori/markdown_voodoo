---
name: chapter-by-chapter
description: Use when executing a markdown task file one chapter at a time, with user approval before each next chapter.
agent: Agent_000
argument-hint: A name for the conversation in double-quotes, like "Button error investigation". A markdown file with chapters and tasks to execute. 
---

# Goal

Run the task file one chapter at a time. Never work on more than one chapter between approvals.

# Approval

Only these phrases approve moving forward:

- `okgo!`
- `continue with next chapter`
- `proceed to next chapter`

Match phrases case-insensitively. Ignore only leading or trailing commas, periods, question marks, and exclamation marks. A question answer is approval only if it also includes one approved phrase.

# Workflow

## Setup

- Parse chapters from the provided markdown file.
- If parsing fails or no chapters are found, tell the user what failed and request a valid markdown task file.
- Create todos: one per chapter, plus a final `Let the user test` todo.

## Chapter Loop

Repeat for each chapter:

- Mark only the current chapter as in-progress.
- Implement only the current chapter.
- Stop for user input if a choice would change behavior, architecture, naming, public interfaces, persistence format, or migration strategy.
- After implementation, ask 2 to 4 concrete validation questions tied to the chapter output.
- Continue only after explicit approval.

Use `vscode_askQuestions` with `allowFreeformInput: true` for decision and validation questions. Decision questions must include 2 to 4 options and the preferred option.

## Final Test

- Mark `Let the user test` as in-progress after all chapters are complete.
- Let the user test the completed work.
- Ask concrete validation questions tied to what changed.
- Finish only after explicit approval.
