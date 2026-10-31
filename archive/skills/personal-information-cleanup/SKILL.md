---
name: personal-information-cleanup
description: Scrub a leaked string (username, file path, email, API token, or any sensitive text) from a git repository's working tree AND its entire history — including a repo already pushed to a public GitHub remote. Backs up first, rewrites history with git-filter-repo (covering both / and \ path forms plus binary blobs), force-pushes, then verifies the string is gone from both local and the freshly re-fetched remote. Use when the user accidentally committed personal or sensitive data and wants it removed.
---

# Personal Information Cleanup

Remove a leaked string from a git repo — working tree **and** full history — and, when the repo has a remote, propagate the cleanup to it. This is the hard case: the repo has **already been pushed to a public GitHub repository**, so it includes a force-push and a remote re-check. (If the repo has no remote, skip the push and remote-verify steps — the local rewrite is then the whole job.)

## Read this first — what this can and cannot do

Rewriting history removes the string from your repo and every *future* clone, fork, and download. It does **not** retroactively erase a public leak:

- Anyone who already cloned or forked the repo keeps the old history.
- GitHub keeps force-pushed commits reachable by their SHA (and across a fork network) until it garbage-collects — which may require contacting GitHub Support.
- Search indexes, archives, and secret-scanning bots may already have copied it.

**Therefore: if the leaked string is a credential (API key, token, password, private key), tell the user to ROTATE / REVOKE it immediately — that is the only real remedy. The history rewrite is secondary.** Treat anything that was public as compromised. Proceed with the cleanup to stop ongoing exposure, but set this expectation with the user up front.

## Preconditions

- The current directory is the top of the git repo (`git rev-parse --show-toplevel`).
- `git-filter-repo` is installed (`pip install git-filter-repo`).
- The working tree is clean (`git status`) — commit or stash anything first, or filter-repo will refuse to run.

---

## Phase 1 — Get the target

Ask the user, in chat:

1. **The exact string to remove** (e.g. a username, a path fragment, an email, a token). Get the literal string — do not guess it.
2. **What to replace it with** — suggest a default based on its shape, and let the user adjust:
   - a bare word / name → a placeholder like `USER` or `REDACTED`
   - an absolute path or path-prefix → collapse the user-specific part to `~`
   - an encoded / flattened form → a neutral token like `WORKSPACE`

Throughout the rest of this skill, `<TERM>` is that string and `<REPLACEMENT>` is its replacement. Use **fixed-string** matching everywhere (`grep -F`, `git grep -F`), because the term may contain regex metacharacters like `\` or `.`.

## Phase 2 — Evaluate the situation (be thorough about paths and slashes)

Find **every** form the string takes, and report what you find. Cover all of these:

- **Bare occurrences** — working tree and history:
  ```bash
  git grep -i -n -F "<TERM>"                      # current tree
  git log --all -S"<TERM>" --oneline              # file contents, across history (pickaxe is literal)
  git log --all --grep="<TERM>" --oneline         # commit / tag messages
  ```
- **Path forms — ALWAYS generate BOTH slash directions.** A path that appears as `…\<TERM>\…` somewhere will appear as `…/<TERM>/…` elsewhere. For every path-context hit, plan a rule for the `\` form **and** the `/` form. Also look for:
  - escaped backslashes in JSON / logs (`\\<TERM>\\`)
  - URL-encoded separators (`%5C`, `%2F`) if the repo holds URLs or logs
- **Encoded / flattened forms** — e.g. a Windows path flattened into one token with separators turned into hyphens (Claude project-dir slugs do this: `C:\Users\<user>\…` → `c--Users-<user>-…`). Search for the term embedded inside such tokens.
- **Binary blobs** — `--replace-text` **silently skips binary**, so text rules will not clean it. Detect binaries that embed the string (compiled bytecode `.pyc`, `.sqlite`/`.db`, packed assets, images with metadata):
  ```bash
  # >0 means some object (possibly binary) still holds it:
  git rev-list --all --objects | awk '{print $1}' | sort -u \
    | git cat-file --batch | grep -a -i -c -F "<TERM>"
  # likely binary culprits ever committed:
  git log --all --diff-filter=A --name-only --format= | sort -u | grep -i -E '\.(pyc|sqlite|db)$'
  ```

**Compile a structured list and print it to the chat**, grouped by form (bare / `\`-path / `/`-path / encoded / binary / commit-message) with file or commit references. Then propose the concrete replacement rules (Phase 5) for the user to eyeball before any change.

## Phase 3 — Back up (mandatory, before anything destructive)

Make a full bundle of every ref so the rewrite is completely reversible.

**Ask the user for the precise location first.** Suggest their home folder (e.g. `~/<repo>-PRE-CLEANUP.bundle`), but let them choose. The bundle must live **outside** the repo.

```bash
git bundle create "<BACKUP_PATH>" --all
git bundle verify "<BACKUP_PATH>"
```

Tell the user: this bundle still contains the leaked string — keep it local, never commit or publish it, and delete it once they are confident.

## Phase 4 — Final confirmation

Show the user the full plan: the replacement rules, any binary files that will be **removed** from history, and the force-push target (`git remote -v`). **Ask once more whether to proceed, and STOP until they say yes.** This is the point of no easy return for the remote.

## Phase 5 — Execute

Write `expr.txt` **outside the repo** (e.g. next to the bundle) so it is never accidentally committed; delete it when done.

1. **Capture the remote URL** — filter-repo removes `origin`, so save it now (adjust if the remote is named differently):
   ```bash
   REMOTE_URL="$(git remote get-url origin)"
   ```
2. **Fix hardcoded source** — if a code file *hardcodes* the value, edit it by hand to derive the value instead (a blunt text-swap leaves broken or fake literals), and commit that first.
3. **Write the expression file** — rules are literal substrings applied **top-to-bottom**, so order **specific → general**: full paths (both slash forms) first, encoded / flattened forms next, the bare term last:
   ```
   C:\Users\<TERM>\Documents==>~
   C:/Users/<TERM>/Documents==>~
   <flattened-encoded-form>==>WORKSPACE
   <TERM>==><REPLACEMENT>
   ```
   Prefix a rule with `regex:` if you need case-insensitive or pattern matching (e.g. `regex:(?i)<TERM>==><REPLACEMENT>`).
4. **Remove offending binaries from history** (the ones Phase 2 found). Only remove files that are safe to drop — junk like `.pyc` goes without question; if a binary is something the user needs (a real database, an image), **flag it and ask** whether to drop it, regenerate it clean, or accept the residue. Adjust the matcher to what you actually found:
   ```bash
   git filter-repo --path-regex '\.pyc$' --invert-paths --force
   ```
5. **Scrub file contents:**
   ```bash
   git filter-repo --replace-text expr.txt --force
   ```
6. **Scrub commit / tag messages** — only if Phase 2 found the term in messages:
   ```bash
   git filter-repo --replace-message expr.txt --force
   ```
7. **Drop old objects** still pinned by the reflog:
   ```bash
   git reflog expire --expire=now --all && git gc --prune=now --aggressive
   ```

> Note: removing a file may leave some commits empty (e.g. a commit whose only change was deleting that file); filter-repo prunes those automatically. Expect the commit count to drop slightly.

## Phase 6 — Verify LOCAL, then push, then verify REMOTE

**a) Local must be clean before pushing** — both must report `0` / no output:
```bash
git rev-list --all --objects | awk '{print $1}' | sort -u | git cat-file --batch | grep -a -i -c -F "<TERM>"
git grep -i -F "<TERM>"
```
If anything remains, **do not push** — investigate (usually another binary, an encoded form, or a missed slash direction) and re-run the relevant pass.

**b) Re-add origin and force-push everything:**
```bash
git remote add origin "$REMOTE_URL"
git push origin --force --all
git push origin --force --tags
```

**c) Verify the REMOTE by fetching it fresh** — clone the pushed remote into a throwaway sibling dir, scan it, then delete it:
```bash
git clone "$REMOTE_URL" ../verify-clone
git -C ../verify-clone rev-list --all --objects | awk '{print $1}' | sort -u \
  | git -C ../verify-clone cat-file --batch | grep -a -i -c -F "<TERM>"   # expect 0
rm -rf ../verify-clone
```

**Report honestly.** A clean fresh clone means new clones and visitors no longer see the string. It does **not** prove the old commits are purged — on GitHub they can stay reachable by SHA, and through any fork, until garbage collection. If that matters, advise the user to: (1) delete forks they control, (2) ask collaborators to re-clone and discard old copies, and (3) contact GitHub Support to GC the dangling commits. And restate: if the string was a secret, it must be rotated regardless of this cleanup.

## Done

Summarize for the user: what was removed, how many commits were rewritten, where the backup bundle lives, the push result, and the local + remote verification counts (both `0`). Remind them to delete the backup bundle once satisfied and never to publish it. Delete the scratch `expr.txt`.
