use crate::document::{Document, entry_text};
use crate::json_path;
use crate::toc::counted;

pub fn render(document: &Document, source: &str, file: &str, path: &str, character_limit: usize) -> Result<String, String> {
    let index = json_path::resolve(document, path)?;
    let entry = &document.entries[index];
    let text = entry_text(source, entry);
    let character_count = text.chars().count();
    if character_count > character_limit {
        let zoom_hint = if document.descendant_count(index) > 0 { "toc shows what is inside, " } else { "" };
        return Err(format!(
            "{path} has {}, over the limit of {character_limit}: {zoom_hint}--limit {character_count} reads it all",
            counted(character_count, "character")
        ));
    }
    let first_line = entry.first_row + 1;
    let last_line = entry.last_row + 1;
    let location = if first_line == last_line {
        format!("{file}:{first_line}")
    } else {
        format!("{file}:{first_line}-{last_line}")
    };
    Ok(format!("{location}\n{text}\n"))
}
