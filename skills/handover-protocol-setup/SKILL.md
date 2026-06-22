---
name: handover-protocol-setup
description: >-
  Set up the HandOver Protocol (HOP) in the current project — a small, single-purpose
  knowledge-continuity setup: the Status.md baton, the HandOver_Protocol.md mechanism doc, and a
  minimal hand-over pointer in CLAUDE.md. Use when bootstrapping a project for long-running,
  multi-session work, or re-applying the protocol to an existing one. Writes only inside the
  current project.
---

# HandOver Protocol setup (HOP)

This skill does exactly **one thing**: install the HandOver Protocol so work survives cleanly
across sessions. It is deliberately option-free — collaboration conventions and other
preferences are out of scope (a separate skill's job).

The meat is the sibling file `HandOver_Protocol.md`; this `SKILL.md` is just the procedure that
stamps it into a project.

After it runs, the protocol is self-sustaining: session start flows `CLAUDE.md` → `Status.md`.
This skill isn't needed again except to update the protocol itself.

## Hard rule

Everything this skill writes stays inside the **current project**. Never touch `~/.claude/` or
any other project. If a step would reach outside the project, stop and ask first.

## What it creates

- `HandOver_Protocol.md` — the stable mechanism doc (it also carries the `Status.md` template).
- `Status.md` — the baton, created from the fenced template inside `HandOver_Protocol.md`.
- A minimal **Hand-over** pointer merged into `CLAUDE.md`, so session start knows to read the
  baton. Nothing else in `CLAUDE.md` is touched.

## Step 1 — Detect

Check the project root for `Status.md`, `HandOver_Protocol.md`, and `CLAUDE.md`.

- None → **init mode** (fresh scaffold).
- Some present → **update mode:** re-apply `HandOver_Protocol.md` only; never overwrite the live
  `Status.md` content. Diff and ask before replacing anything that holds real content.

## Step 2 — Confirm

Tell the user what will be created (the three items above), then askUserQuestion once to proceed. Treat
**"Go ahead"** or **"okgo"** as approval.

## Step 3 — Scaffold (after approval)

- Copy this skill's `HandOver_Protocol.md` into the project root.
- Create `Status.md` from the fenced `markdown` baton block inside `HandOver_Protocol.md`
  (extract it verbatim — that block is the canonical starter).
- Merge a **Hand-over** section into `CLAUDE.md` (create the file if absent, titling it from the
  project folder name). Leave any existing content intact; skip if the section is already there:

  > ## Hand-over
  >
  > Long-running, multi-session project. At session start, read **`Status.md`** for the current
  > state and next step; the mechanism is in **`HandOver_Protocol.md`** (HOP).

## Step 4 — Confirm and step back

List what was created or merged. Note the protocol is now self-sustaining and this skill isn't
needed again unless updating it. Leave all changes in the working tree (the user commits).
