# Haven mail forwarding subject format

Wally's idea: a mail from a known sender, with a subject in this format, is forwarded as it is, content and attachments.

- The format: `<letter or short name> <arrow> <exact seat name>`, like `wally → tool_builder`.
- The short name may be `S`, `S.`, `"S"` or `Ⓢ`; the arrow may be any arrow, like `->`, `→`, `⇨` or `➡️`.
- Trailing whitespace is fine; any other deviation, a typo included, needs clearance.
- Only for known senders, and no hard rule: common sense and the thresholds, as usual.
- When Wally makes a typo, the postmaster answers with exactly this, and nothing about the typo:

  ```
  Hey Wally!
  Made a typo there, mate?
  greetings
  ```

- The protocol belongs in the postmaster's README; calm-email could add `forward <number>` without a seat, taking the seat from a subject in the exact format.
