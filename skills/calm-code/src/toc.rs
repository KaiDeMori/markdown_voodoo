use crate::outline::{Entry, Outline};

const PAGE_SIZE: usize = 100;
const KIND_WORDS: [&str; 7] = ["class", "struct", "interface", "record", "method", "property", "function"];

pub fn render(outline: &Outline, name_path: &[String], page: usize) -> Result<String, String> {
    let scope_root = match name_path {
        [] => None,
        _ => Some(outline.resolve(name_path, true)?),
    };
    let base_depth = scope_root.map_or(0, |root| outline.entries[root].depth);
    let scope_size = match scope_root {
        Some(root) => 1 + outline.descendant_count(root),
        None => outline.entries.len(),
    };
    let is_collapsed = scope_size > PAGE_SIZE;
    let (pinned, listed): (Option<usize>, Vec<usize>) = if is_collapsed {
        (scope_root, outline.children_of(scope_root))
    } else {
        let first = scope_root.unwrap_or(0);
        (None, (first..first + scope_size).collect())
    };

    let page_count = listed.len().div_ceil(PAGE_SIZE).max(1);
    if page > page_count {
        return Err(format!("no page {page}, the last is page {page_count}"));
    }
    let page_entries = &listed[(page - 1) * PAGE_SIZE..listed.len().min(page * PAGE_SIZE)];
    let largest_number = pinned.iter().chain(page_entries).map(|&index| outline.entries[index].number).max();
    let number_width = largest_number.map_or(0, |number| format!("@{number}").len() + 2);

    let mut lines = vec![header_line(outline)];
    if outline.syntax_error_count > 0 {
        lines.push(format!(
            "{}, the list may be incomplete",
            counted(outline.syntax_error_count, "syntax error")
        ));
    }
    if let Some(root) = pinned {
        lines.push(entry_line(&outline.entries[root], base_depth, number_width, None));
    }
    for &index in page_entries {
        let inside_count = is_collapsed.then(|| outline.descendant_count(index));
        lines.push(entry_line(&outline.entries[index], base_depth, number_width, inside_count));
    }
    if page_count > 1 {
        let next = if page < page_count { format!(", next: --page {}", page + 1) } else { String::new() };
        lines.push(format!("page {page} of {page_count}{next}"));
    }
    Ok(lines.join("\n") + "\n")
}

fn header_line(outline: &Outline) -> String {
    let counts: Vec<String> = KIND_WORDS
        .iter()
        .filter_map(|&word| {
            let count = outline.entries.iter().filter(|entry| entry.kind_word() == word).count();
            (count > 0).then(|| counted(count, word))
        })
        .collect();
    let summary = if counts.is_empty() { "nothing to list".to_string() } else { counts.join(", ") };
    format!("{}, {}: {summary}", outline.language_name, counted(outline.line_count, "line"))
}

fn entry_line(entry: &Entry, base_depth: usize, number_width: usize, inside_count: Option<usize>) -> String {
    let number = format!("@{}", entry.number);
    let indentation = "  ".repeat(entry.depth - base_depth);
    let lines = counted(entry.line_count(), "line");
    let weight = match inside_count {
        Some(count) if count > 0 => format!("{lines}, {count} inside"),
        _ => lines,
    };
    format!("{number:<number_width$}{indentation}{} ({weight})", entry.label)
}

pub fn counted(count: usize, word: &str) -> String {
    match count {
        1 => format!("1 {word}"),
        _ if word.ends_with('s') => format!("{count} {word}es"),
        _ if word.ends_with('y') => format!("{count} {}ies", &word[..word.len() - 1]),
        _ => format!("{count} {word}s"),
    }
}
