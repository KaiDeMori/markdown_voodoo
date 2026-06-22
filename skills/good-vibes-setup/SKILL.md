---
name: good-vibes-setup
description: >-
  Set up a project's collaboration conventions ("good vibes") — an interactive install wizard
  that walks the user, one self-contained question at a time, through opt-in working agreements
  for knowledge/memory, collaboration style, naming, plans, and git commits, then merges the
  chosen ones into the project's CLAUDE.md. Use when bootstrapping a project's working agreement
  or revisiting it. Writes only inside the current project.
---

# Good vibes setup 🤗

This skill installs a project's **collaboration conventions** — the small working agreement that
makes a human + agent pair pleasant and predictable. It is the conventions counterpart to the
`handover-protocol-setup` skill (which installs only the HandOver Protocol); the two are separate
concerns and this one stays in its lane.

It runs as an **install wizard**: called once, it walks the user through a short series of
questions and merges the chosen conventions into the project's `CLAUDE.md`. After it runs it
isn't needed again, except to revisit the agreement.

## Hard rule

Everything this skill writes stays inside the **current project's `CLAUDE.md`**. Never touch
`~/.claude/` or any other project. If a step would reach outside the project, stop and ask first.

## What it changes

- Merges the **selected** convention sections (below) into the project root `CLAUDE.md`, creating
  the file if absent (title it from the project folder name). Nothing already in `CLAUDE.md` is
  disturbed except sections the user explicitly chooses to replace.

## How the wizard works

Present **one self-sufficient `AskUserQuestion` dialog per convention**. Each dialog must stand
entirely on its own:

- The **question** carries a short, plain-language explanation of the topic — the user should not
  need outside context to answer.
- **Every option** carries its own one-line explanation of what choosing it means.
- The **free-text field is automatic** — `AskUserQuestion` always appends an "Other" option. Treat
  any free-text answer as the user's own wording for that convention and write *that* verbatim
  under the section heading instead of a canned text. Mention in the topic blurb that they can type
  their own version.
- Put the **recommended** option first and label it "(Recommended)".

Ask the five questions in as few `AskUserQuestion` calls as the tool allows (up to four questions
per call — e.g. three then two), keeping each question self-sufficient. If the user is clearly
going slowly or wants to discuss, drop to one at a time.

## Step 1 — Detect

Read the project root `CLAUDE.md` (note if it's absent — you'll create it on first write). Scan
for any convention section headings that already exist (`## Knowledge and memory`,
`## Collaboration style`, `## Naming`, `## Plans`, `## Git commits`). For any that are present,
add a **"Keep what's already there"** option to that convention's dialog and make it the default.

Briefly tell the user what's about to happen ("I'll walk you through five collaboration
conventions; pick or skip each, or type your own"), then run the wizard.

## Step 2 — Run the wizard

The five questions. The blockquote under each option is the **exact text** to merge into
`CLAUDE.md` when that option is chosen.

### 1. Knowledge & memory — header chip: `Memory`

*Topic:* Where this project's knowledge lives, and whether the agent uses its own cross-session
memory.

- **Workspace-only, ask before any memory (Recommended)** — knowledge lives as markdown in the
  repo; agent memory is off by default and needs explicit approval.

  > ## Knowledge and memory
  >
  > All knowledge for this project lives in the workspace, as markdown in this repo — state,
  > decisions, plans, and session-to-session hand-offs. Treat agent memory as off by default: when
  > you learn something worth keeping, write it to the appropriate workspace file. If something
  > genuinely seems to belong in agent memory, ask first and get explicit approval before writing
  > it.

- **Workspace-first, memory allowed** — prefer repo files, but the agent may also use memory for
  durable facts without asking.

  > ## Knowledge and memory
  >
  > Project knowledge lives in the workspace as markdown in this repo — state, decisions, plans,
  > and hand-offs — so it survives across sessions and tools. Agent memory may also be used for
  > durable, cross-session facts; prefer the workspace when in doubt.

- **No convention on this** — write nothing about knowledge/memory.

### 2. Collaboration style — header chip: `Collab style`

*Topic:* How ideas get proposed, judged, and argued during design and brainstorming.

- **Shared pile of ideas, merit-sorted (Recommended)** — ideas pooled and sorted by quality, not
  by who proposed them.

  > ## Collaboration style
  >
  > Brainstorm and design as one shared pile of ideas, sorted for quality regardless of who
  > proposed them. Engage on merit, build on each other's ideas, and push back freely — what
  > matters is the idea, not who proposed it or who turned out right.

- **Lighter touch** — a one-line version of the same spirit.

  > ## Collaboration style
  >
  > Judge ideas on merit, not on who proposed them. Build on good ideas and push back freely.

- **No convention on this** — write nothing about collaboration style.

### 3. Naming — header chip: `Naming`

*Topic:* How things (files, functions, concepts) get named in this project.

- **Descriptive, multi-word names (Recommended)** — names that read on their own; a strong
  preference, not a hard rule.

  > ## Naming
  >
  > Descriptive, multi-word names: give each thing a name that says what it is — usually three or
  > more words, semantically strong enough to read on its own. (Strong preference, not a hard rule
  > — especially for code.)

- **No convention on this** — write nothing about naming. *(If they have a house naming standard,
  the free-text field is the place to paste it.)*

### 4. Plans — header chip: `Plans`

*Topic:* How written plans refer to code, and whether claims are tagged by how settled they are.

- **Name things, tag firmness (Recommended)** — refer by name (not line numbers) and mark each
  claim decided / leaning / open.

  > ## Plans
  >
  > In any plan, refer to sections, functions, or concepts by name — names survive as code moves;
  > line numbers rot. Tag each claim with how firm it is: **[decided]** (build on it), **[leaning]**
  > (current preference, not locked), **[open]** (genuinely undecided).

- **Name things, no firmness tags** — just the "refer by name, not line numbers" half.

  > ## Plans
  >
  > In any plan, refer to sections, functions, or concepts by name — names survive as code moves;
  > line numbers rot.

- **No convention on this** — write nothing about plans.

### 5. Git commits — header chip: `Git commits`

*Topic:* Who runs git, and whether the agent may commit or push.

- **User commits manually (Recommended)** — the agent makes changes and leaves them in the working
  tree; the user runs all git.

  > ## Git commits
  >
  > The user does all git commits manually. Make and save your changes, then leave them in the
  > working tree — every `git commit` and `git push` is the user's to run.

- **Agent may commit when asked** — the agent can run git, but only on explicit request.

  > ## Git commits
  >
  > The agent may run `git commit` and `git push`, but only on the user's explicit request — never
  > proactively. Otherwise, leave changes in the working tree.

- **No convention on this** — write nothing about git commits.

## Step 3 — Merge (after the wizard)

- Append each chosen section to `CLAUDE.md` (create the file if absent, titling it from the
  project folder name). Keep all existing content intact.
- If a chosen section's heading already exists: replace its body only when the user picked a
  concrete option for it; if they chose **"Keep what's already there"**, leave it untouched.
- For any **free-text** answer, write the user's wording verbatim under the matching `## ` heading.
- Be idempotent — running the wizard twice with the same answers must not duplicate sections.

## Step 4 — Confirm and step back

List what was written, replaced, or skipped. Note that the conventions now live in `CLAUDE.md` and
this skill isn't needed again unless revisiting the agreement. Leave all changes in the working
tree (the user commits).
