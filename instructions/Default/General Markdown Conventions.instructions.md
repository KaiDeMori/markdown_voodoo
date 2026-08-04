---
description: Read this before writing or editing markdown files. It describes the conventions to follow when writing markdown content.
applyTo: '**'
---

# General formatting

* use headings and subheadings to structure the content
* use "#" for main headings, "##" for subheadings, and so on
* use bullet points for lists of items or steps where the order does not matter
* use numbered lists only when the order of steps matters
* use code blocks for code snippets or commands
* use checkboxes for tasks or items that can be marked as done

# Code Blocks

Single tick marks are for inline code only.
If there is more than one line of code, you must use triple tick marks to create a code block.
If the language of the code block is known, specify it after the opening triple tick marks for syntax highlighting.
All code, including command line instructions, **must** be placed in code blocks.

# Open Questions

It is generally prefered to use the `vscode/askQuestions` tool and only reserved to resolve complex questions.
If there really are any open questions or uncertainties about the content left, list them in a separate section at the end of the document called "Open Questions".

```markdown
## Question Title
A clear and concise question about the content.

**Answer**: If there is an answer to the question, provide it here. If not, leave it blank.
```

# No clutter

Do not add any extra clutter like timestamps or "status notes".

Examples of what **not** to do:

* Don't add timestamps or 'last changed' notes
* Don't include testing plans or Testing Checklist
* Don't perform complexity calculations
* Don't provide time estimates
* Don't outline committing plans

Never do any of those since they are just wasted energy.
Instead focus on the actual task at hand.

# Numbering only when absolutely necessary

Only use numbered lists when the order of steps matters!
Never use numbered lists for checklists or when the order does not matter.
