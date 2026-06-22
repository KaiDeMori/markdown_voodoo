---
name: okgo
description: Use this to implement a given plan in a markdown file
agent: Agent_000
---

the name of the conversation is exactly the user prompt in quotation marks. do not include "okgo" in the name.

# Goal
Execute the given implementation plan one section at a time with hard approval gates.

Start by creating a todo list item for each section of the plan, then go through them one by one.

# Required Workflow
- Parse chapters from the provided markdown file.
- Divide plan into sections and create one todo entry per section.
- The final todo item must always be:
	- Let the user test
	- Let the user test and askQuestions that are specific (example: "Do you see the profiles in the vscode settings tab?").

For each section, follow this exact sequence:
1. Mark only that section as in-progress.
2. Work on only that section until completion, unless an important decision is reached.
3. If an important decision is reached, pause immediately and ask a decision question before continuing.
4. Wait for explicit user approval on that decision, then continue the same section.
5. After finishing the section, stop and ask validation questions before starting any next section.
6. Ask 2 to 4 section-specific validation questions with vscode_askQuestions.
7. Set allowFreeformInput to true for every question.
8. Wait for explicit user approval before continuing.
9. Start the next section only after explicit approval.

Accepted approval examples:
- okgo!
- Continue with next section
- Proceed to next section

If explicit approval is missing, do not implement the next section and keep asking questions until approval is given.

# Question Modes

## Validation Question Case (after section completion)
- Questions must be concrete and testable.
- Questions must be tied to the section output.
- Avoid generic prompts.
- Use allowFreeformInput true.

## Important Decision Case (during section work)
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
Starting the next section before explicit approval is considered a failure, even if the implementation is correct.
Proceeding past an important decision point without a user decision is also considered a failure.

