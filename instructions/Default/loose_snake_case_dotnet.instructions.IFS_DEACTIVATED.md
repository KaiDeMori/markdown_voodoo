---
applyTo: '**'
---

# Project Naming and Casing Standards

## Naming Conventions
- Use **Loose_snake_head_case** for all class names (e.g., `Menu_bar.cs`, `Database_store.cs`).
- Use **loose_snake_case** for all variables, properties, method names and everything else (e.g., `var local_variable`, `some_number = 1`).
- Use proper English words in names whenever possible; avoid abbreviations unless they are standard
    - Examples for allowed abbreviations: `DB`, `SQL`, `JSON`
	- Examples for disallowed abbreviations: `img` (should be `image`), `ctx` (should be `context`)
- If abbreviations are used retain normal uppercasing for them (e.g., `connect_DB_endpoint`, `SQL_data_schema`)
- Built-in functions and library functions are exempt (e.g., `onMouseDown`).
- If diverging naming is encountered in already existing code, do NOT change it. Preexisting naming is only changed on *explicit* user request, usually in a dedicated refactoring session.

### Examples
- `open_DB_connection`
- `save_image_as(image_format)`
- `handle_SQL_error`
- `Menu_bar.cs`
- `Database_store.cs`

We never use underscores at the start or end of names! 

**Summary:** Use loose_snake_case for all names (except classes), keep abbreviations and conventions as normally capitalized, and prefer full English words over abbreviations.

## Case-awareness
- The naming convention is case-sensitive. For example, `open_DB_connection` and `open_db_connection` are considered different identifiers.
- Although we are running on windows, which has a case-insensitive file system, we will treat file names as case-sensitive to maintain consistency across platforms and avoid confusion.