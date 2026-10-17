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

- MIME detection: `file` reads the bytes that arrived, and catches a server that announces one type and delivers another.
- Token counting: calm-fetch asks the token counter, so the hall keeps one counter.
- Markdown: a local step of its own, once a real use asks for it.

## Open

- Ravens outside this repo have no `ws:/scratchpad/`; where do their fetches land?
