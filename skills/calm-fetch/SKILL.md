---
name: calm-fetch
description: >-
  hallmark_tool
  A calm fetch: a URL lands raw in the workspace's scratchpad, and only one line enters the window.
  Use when a raven wants a page or a file from the web without a model in between and without surprises in size.
---

# calm-fetch

```
bash C:/Users/devboese/.claude/skills/calm-fetch/calm_fetch.sh <url> [limit_in_megabytes]
```

It fetches the URL raw with curl into the workspace's `scratchpad/fetched/`, and prints one line:

```
text/html, 6 KB -> C:/.../scratchpad/fetched/peopleoftheprompt.org_Notes_on_a_Quiet_Universe_index.html
application/pdf, 16.2 MB: over the limit of 5 MB, not fetched
404 from the server, not fetched
```

- The limit is 5 MB by default; a raven who still wants a bigger file raises it for that one call.
- It reads the server's headers first, so an announced size over the limit stops the fetch before any content arrives.
  Without an announced size, it checks after the fetch, and a file over the limit is not kept.
- The whole path names the file, with slashes turned into underscores; a second fetch of the same name gets a number, and nothing is overwritten.
- The line shows the file's full path, ready for Read or self-flow.
- Exit 0 means the file is there.
- What comes next is the raven's choice: count it with the token counter, read a part, or flow it.
- The default limit and the timeout are the variables at the top of `calm_fetch.sh`.

'nough said.
