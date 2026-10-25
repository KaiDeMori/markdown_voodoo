# calm-css

otis_builder's wish: a calm look at a folder of stylesheets, telling which parts do nothing.

- Three kinds of nothing: a selector whose class, id or attribute appears in no markup; a declaration that a later rule of equal or higher specificity on the same element always overrides; a rule that repeats another rule.
- In Otis, almost no markup is HTML: pages are built by script, so the markup to read is every string literal in `src/**/*.ts`, plus `index.html` and the manual's template.
- A class built from parts, such as `fixed-actions-${position}`, cannot be matched; the tool names such selectors as unsettled instead of counting them as unused.
- `calm-css <styles_folder> [markup_folder]`: one line per stylesheet, such as `prompt_box.css: 2 selectors match nothing, 1 overridden, 0 duplicates, 1 unsettled`.
- `calm-css where <stylesheet>`: each finding with its selector, and the rule that overrides it.
- `calm-css what <stylesheet> <selector>`: the rule's lines, and for an overridden one, the overriding rule's lines beside them.
- Exit 0 when the look ran; the full report stays in the scratchpad, as with calm-vitest.
- The cuts stay by hand, in the pane, with Wally.
