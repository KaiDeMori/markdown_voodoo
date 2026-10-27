use crate::outline::Outline;
use crate::toc::counted;

pub fn render(
    outline: &Outline,
    source: &str,
    file: &str,
    name_path: &[String],
    character_limit: usize,
) -> Result<String, String> {
    let entry = &outline.entries[outline.resolve(name_path, false)?];
    let lines: Vec<&str> = source.lines().skip(entry.first_row).take(entry.line_count()).collect();
    let text = lines.join("\n");
    let character_count = text.chars().count();
    if character_count > character_limit {
        let zoom_hint = if entry.is_container() { "toc shows what is inside, " } else { "" };
        return Err(format!(
            "{} has {}, over the limit of {character_limit}: {zoom_hint}--limit {character_count} reads it all",
            entry.label,
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
