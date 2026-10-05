# End-to-end test: unicode-glyph-render

Hi Opus! Wally and Opus, the tool builders, would love your help testing a tool: the unicode-glyph-render skill.
Rules: use only what its SKILL.md tells you. Please don't read render_glyph.py or other files in the skill folder; we want to know whether SKILL.md is enough.

Please work through these questions, the way you'd answer a user:

1. What does the character U+A66E look like? How many eyes does it have?
2. Is there a visible difference between ❤ and ❤️? And between 1⃣ and 1️⃣?
3. Show "a -> b != c 😀❤️ꙮ" in Fira Code Retina, with emoji from Segoe UI Emoji. Which font drew which part?
4. The same text, but with only those two fonts and nothing else.
5. Render "x => y" in Fira Code.
6. Show the family emoji 👨‍👩‍👧 and the flag of Scotland.
7. What does a zero-width space between "a" and "b" look like?
8. Render the line "Hello שלום world".
9. Render a sentence of about 80 characters, then read it back from the image.
10. Which bundled fonts cover the Hindi conjunct क्ष?
11. Is "a -> b" drawn with a ligature in Fira Code Retina? How can you tell?
12. Render the two lines "first line" and "second line" in one image.

Along the way, note roughly how long each call takes.

Finally, please write a short report:

- what worked,
- what in SKILL.md was unclear, or what you had to guess,
- bugs and feature requests, each one with input, expected result and actual result.
