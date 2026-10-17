# calm-fetch: loose notes

## The idea

WebFetch is loud: nobody knows how much comes back, and a model in between decides what the raven gets.
calm-fetch fetches a URL raw into the scratchpad, and only one line enters the window.

## The sketch

```
calm_fetch.sh <url> [limit_in_megabytes]
text/html, 85 KB -> scratchpad/example.org_index.html
application/pdf, 16.2 MB: over the limit of 5 MB, not fetched
```

- It asks the server first, so it knows the type and size before any content arrives.
- Over the limit, it stops and says so; a raven who still wants the file raises the limit for that one call.
- Under the limit, curl fetches it raw: no service and no model in between.

## Later

- Markdown: a local step of its own, once a real use asks for it.

## Decided

- Fetches land in the current workspace's `scratchpad/fetched/`, created when it is missing.
- The whole path names the file, slashes turned into underscores: `example.org_docs_index.html`.
- `file` checks the bytes; when text and binary don't match the announced type, the line names the real type, and the file gets its extension.
- Counting is the raven's: it hands the path to the token counter, and calm-fetch stays independent.
