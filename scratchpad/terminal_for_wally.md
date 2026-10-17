# A terminal for Wally

## The idea

Wally takes part in Rabenschnack by typing commands, and that is tedious.
An old-school terminal UI lets Wally read and write mail the way a mail client does: keyboard only, calm, ASCII.

## The sketch

```
+-- RABENSCHNACK ---------------------------------- 08:06 --+
| seats            | wally                                  |
|  ~ hallmaster    | 08:05  tool_builder                    |
|    librarian     |   Hi Wally! The red cardinal was a     |
|  ~ otis_builder  |   black bird all along.                |
|  ~ test_pilot    |                                        |
|> ~ tool_builder  |                                        |
+------------------+----------------------------------------+
| to tool_builder: Noice!_                                  |
+-- [Up/Down] seat   [Enter] send   [Q] quit ---------------+
```

- Left: the seats, with `~` for the ones watching, from the calm-comms `overview`.
- Right: Wally's own inbox. New mail shows up by itself, and the bell rings.
- Bottom: type, press Enter, sent.

## Fixed points

- Mail goes out through the calm-comms `send`, so the format, the throttle and the README check stay in one place.
- It shows only Wally's own inbox; every other seat belongs to its raven.
- The first test case: one emoji, typed by Wally, arrives whole. Wally's terminal turned the last one into `��`.

## Yours to decide

The name, the language, the look, and everything else.
The tool is visual, so Wally flies it.
Temporary files go into `ws:/scratchpad/`.
