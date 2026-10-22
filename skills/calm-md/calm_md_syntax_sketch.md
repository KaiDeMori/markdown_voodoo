# calm-md syntax sketch

Example calls to juggle with; nothing here is built yet.

## toc

A small doc: the whole tree, as today, each chapter with its number and its weight in words.
All word counts are estimates!

```
$ calm-md toc notes.md
@1  # Notes (1450 words)
@2    ## Attachments (520 words)
@3      ### Steps (140 words)
@4    ## Receiving (95 words)
```

A big doc: one level only, and the first line says why.

```
$ calm-md toc dictionary.md
340 chapters, more than a page: one level shown; zoom in with a title path.
@1   # Dictionary (31000 words, 12 inside)
@2     ## A (2300 words, 30 inside)
@33    ## B (1900 words, 25 inside)
...
```

Zooming in, by title or by number:

```
$ calm-md toc dictionary.md A
$ calm-md toc dictionary.md @2
@2   ## A (2300 words, 30 inside)
@3     ### Abacus (70 words)
@4     ### Abandon (45 words)
...
```

A level with more than 100 chapters, page by page:

```
$ calm-md toc glossary.md Terms --page 2
@2   ## Terms (11000 words, 240 inside)
@103   ### Margin (30 words)
...
page 2 of 3
```

## Numbers

A number is a chapter's place in reading order, so the next chapter is one higher.
Numbers are for looking; changing takes the chapter's title.

```
$ calm-md read notes.md @3
### Steps
...

$ calm-md read notes.md @4

$ calm-md replace notes.md Attachments Steps <<'END'
teh quick
the quick
END
```

## find

```
$ calm-md find notes.md fox
@3  Notes > Attachments > Steps: ...the quick brown fox jumps over the lazy dog...
@4  Notes > Receiving: ...and no fox was harmed in the making of...
2 hits

$ calm-md find notes.md the
23 hits, more than 10: try a longer word, or a title path.

$ calm-md find notes.md fox Attachments
@3  Notes > Attachments > Steps: ...the quick brown fox jumps over the lazy dog...
1 hit
```

## Decided

- `@3` names a chapter by its number, since `#3` would start a comment in bash; line numbers stay written out, like `line 4`, and are only shown.
- `find` matches word starts, case-insensitive: `fox` finds `foxes`, and `the` leaves `other` alone.
- Numbers are for looking, in `toc`, `read` and `find`; `write` and `replace` take titles, so a number that shifted never changes the wrong chapter.
