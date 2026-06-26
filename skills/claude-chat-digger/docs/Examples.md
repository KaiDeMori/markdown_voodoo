# Examples

`<session_id>` and `<uuid>` come from the output of an earlier command: `search` prints session ids, `in` prints message uuids. The search terms, paths, and ids below are illustrative.

## First run

```
python CCD.py index            # build the index (required before searching)
python CCD.py status           # show counts and whether a rebuild is due
```

## search — find conversations

```
python CCD.py search "rate limiter"
python CCD.py search "webhook retry" --limit 5
python CCD.py search "auth token refresh" --all          # all three words in one message
python CCD.py search "migrat*" --mode wildcard
python CCD.py search "deadlock" --role assistant --date-from 2025-01-01
python CCD.py search "TODO" --workspace ~/projects/todo-app
```

Sample output:

```
'rate limiter' — 18 matches across 2 conversations

 1. [12] Add request throttling to the API gateway
      when    : 2025-02-14 09:31
      project : /home/user/projects/api-gateway
      session : 3f2a9c10-7b4e-4d61-8a2c-0e1f2a3b4c5d
      entries : 6 matched
```

## in — matches inside one conversation

```
python CCD.py in <session_id> "rate limiter"
python CCD.py in <session_id> "retry" --context 4
```

Each result line `- <type> <time>  <uuid>` (type is `user` or `assistant`) carries the uuid to hand to `show`.

## show — read a full message

```
python CCD.py show <session_id> <uuid>
python CCD.py show <session_id> <uuid> --block 2        # just one content block
python CCD.py show <session_id> <uuid> --thinking       # include thinking blocks
```

## origin — trace a file

```
python CCD.py origin config.json
python CCD.py origin schema.sql --mode created
python CCD.py origin app.css --tool Write,Edit
```

`filename` is matched against the recorded path's basename, case-insensitively, so it is found wherever it lives.

## tree — draw a fork family

```
python CCD.py tree <session_id>
python CCD.py tree <session_id> --detail short
python CCD.py tree <session_id> --format dot -o conversation.dot
python CCD.py tree <session_id> --single --detail full
```

## family / families — fork relationships

```
python CCD.py family <session_id>
python CCD.py families
python CCD.py families --workspace ~/projects/todo-app --limit 10
```

## list — browse conversations

```
python CCD.py list
python CCD.py list --limit 100
```

## --out — save a result to a file

Every command takes `--out`/`-o`. The file holds the result; a one-line receipt prints to the console.

```
python CCD.py search "rate limiter" -o matches.txt
python CCD.py show <session_id> <uuid> -o message.txt
python CCD.py tree <session_id> --format graph_json -o tree.json
```

Use it for large results — keep the bulk on disk instead of in the terminal. Prefer it over `> file`, which on PowerShell writes UTF-16/BOM/CRLF and corrupts JSON or diagram source.
