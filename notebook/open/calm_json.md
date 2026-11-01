# calm-json

A calm look at a JSON file: its keys at a glance, and the value at one path, without the whole file entering the window.

- Its own tool, not part of calm-code: code asks what is defined where, while data asks what keys are in here, how big each part is, and what sits at a path.
- The zoom goes by path, such as `hooks.UserPromptSubmit[0]`.
- JSONL comes later, once a real use asks for it: one record per line as a zoom level above the keys, and streaming, since those files can be huge.
