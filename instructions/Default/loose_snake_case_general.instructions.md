---
applyTo: '**'
---

# Project Naming and Casing Standards

## Naming Conventions
- Use **Loose_snake_head_case** for all class names and files that contain classes (e.g., `Menu_bar.cs`).
- Use **loose_snake_case** for all variables, properties, method names and everything else (e.g., `var local_variable`). This includes filenames for web documents and resources that do not contain classes (e.g., `index.html`).
- Use proper English words in names whenever possible; avoid abbreviations unless they are standard
    - Examples for allowed abbreviations: `DB`, `SQL`, `JSON`, `UI`, `API`
	- Examples for disallowed abbreviations: `img` (should be `image`), `ctx` (should be `context`)
- If abbreviations are used retain normal uppercasing for them (e.g., `connect_DB_endpoint`)
- Built-in functions and library functions are exempt (e.g., `onMouseDown`, `toString`).
- If diverging naming is encountered in already existing code, do NOT change it. Preexisting naming is only changed on *explicit* user request, usually in a dedicated refactoring session.

### Examples
- `open_DB_connection`
- `save_image_as(image_format)`
- `handle_SQL_error`
- `Menu_bar.cs`
- `Component_registry.cs`
- `app.css`
- `app.js`
- `index.html`
- `var local_variable`
- `some_number = 1`

We never use underscores at the start or end of names! 

**Summary:** Use loose_snake_case for all names (except classes/files), keep abbreviations and conventions as normally capitalized, and prefer full English words over abbreviations.

## Case-awareness
- The naming convention is case-sensitive. For example, `open_DB_connection` and `open_db_connection` are considered different identifiers.
- Although we are running on windows, which has a case-insensitive file system, we will treat file names as case-sensitive to maintain consistency across platforms and avoid confusion.