---
name: chapter-by-chapter_old
description: Use when a markdown task file should be executed strictly chapter-by-chapter with mandatory questions and explicit approval between chapters.
agent: Agent_000
argument-hint: A name for the conversation in double-quotes, like "Button error investigation". A markdown file with chapters and tasks to execute. 
---

# Goal
Execute the task file one chapter at a time with hard approval gates.

# Required Workflow
- Parse chapters from the provided markdown file.
- Create one todo entry per chapter, preserving chapter order.
- The final chapter/todo must always be:
	- Let the user test
	- Let the user test and askQuestions that are specific (example: "Do you see the profiles in the vscode settings tab?").

For each chapter, follow this exact sequence:
1. Mark only that chapter as in-progress.
2. Work on only that chapter until completion, unless an important decision is reached.
3. If an important decision is reached, pause immediately and ask a decision question before continuing.
4. Wait for explicit user approval on that decision, then continue the same chapter.
5. After finishing the chapter, stop and ask validation questions before starting any next chapter.
6. Ask 2 to 4 chapter-specific validation questions with vscode_askQuestions.
7. Set allowFreeformInput to true for every question.
8. Wait for explicit user approval before continuing.
9. Start the next chapter only after explicit approval.

Accepted approval examples:
- okgo!
- Continue with next chapter
- Proceed to next chapter

If explicit approval is missing, do not implement the next chapter and keep asking questions until approval is given. If no more questions are available, simply ask for approval again.

# Question Modes

## Validation Question Case (after chapter completion)
- Questions must be concrete and testable.
- Questions must be tied to the chapter output.
- Avoid generic prompts.
- Use allowFreeformInput true.

## Important Decision Case (during chapter work)
- Important decisions must be made by the user, not the agent.
- If a decision changes behavior, architecture, naming, public interfaces, persistence format, or migration strategy, ask first.
- Do not continue implementation past that decision point until the user answers.
- Ask with vscode_askQuestions and allowFreeformInput true.
- The decision question must include:
	- what decision is needed
	- 2 to 4 concrete options
	- the agent preferred option
	- a short reason why that option is preferred
	- a request for explicit approval before proceeding

# Non-Compliance Rule
Proceeding past an important decision point without asking for a user decision is considered a failure.
Yielding before the last chapter is completed and explicit approval is given is considered a failure.
Do **NOT** end the session until all tasks are completed.