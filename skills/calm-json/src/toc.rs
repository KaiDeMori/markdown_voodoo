use crate::document::{Document, Entry, entry_text};
use crate::json_path;

const PAGE_SIZE: usize = 100;

pub fn render(document: &Document, source: &str, path: Option<&str>, page: usize) -> Result<String, String> {
    let scope_root = match path {
        None => None,
        Some(path) => Some(json_path::resolve(document, path)?),
    };
    let base_depth = scope_root.map_or(0, |root| document.entries[root].depth);
    let scope_size = match scope_root {
        Some(root) => 1 + document.descendant_count(root),
        None => document.entries.len(),
    };
    let is_collapsed = scope_size > PAGE_SIZE;
    let (pinned, listed): (Option<usize>, Vec<usize>) = if is_collapsed {
        (scope_root, document.children_of(scope_root))
    } else {
        let first = scope_root.unwrap_or(0);
        (None, (first..first + scope_size).collect())
    };

    let page_count = listed.len().div_ceil(PAGE_SIZE).max(1);
    if page > page_count {
        return Err(format!("no page {page}, the last is page {page_count}"));
    }
    let page_entries = &listed[(page - 1) * PAGE_SIZE..listed.len().min(page * PAGE_SIZE)];
    let largest_number = pinned.iter().chain(page_entries).map(|&index| document.entries[index].number).max();
    let number_width = largest_number.map_or(0, |number| format!("@{number}").len() + 2);

    let mut lines = vec![header_line(document, source)];
    if let Some(root) = pinned {
        lines.push(entry_line(source, &document.entries[root], base_depth, number_width, None));
    }
    for &index in page_entries {
        let inside_count = is_collapsed.then(|| document.descendant_count(index));
        lines.push(entry_line(source, &document.entries[index], base_depth, number_width, inside_count));
    }
    if page_count > 1 {
        let next = if page < page_count { format!(", next: --page {}", page + 1) } else { String::new() };
        lines.push(format!("page {page} of {page_count}{next}"));
    }
    Ok(lines.join("\n") + "\n")
}

fn header_line(document: &Document, source: &str) -> String {
    let summary = document.root_summary.as_deref().unwrap_or("nothing to list");
    format!(
        "JSON, {}, {}: {summary}",
        counted(document.line_count, "line"),
        counted(source.chars().count(), "character")
    )
}

/// A scalar shows its value in its label; an object or array adds its weight in characters.
fn entry_line(source: &str, entry: &Entry, base_depth: usize, number_width: usize, inside_count: Option<usize>) -> String {
    let number = format!("@{}", entry.number);
    let indentation = "  ".repeat(entry.depth - base_depth);
    let weight = if entry.kind.is_container() {
        let characters = counted(entry_text(source, entry).chars().count(), "character");
        match inside_count {
            Some(count) if count > 0 => format!(" ({characters}, {count} inside)"),
            _ => format!(" ({characters})"),
        }
    } else {
        String::new()
    };
    format!("{number:<number_width$}{indentation}{}{weight}", entry.label)
}

pub fn counted(count: usize, word: &str) -> String {
    match count {
        1 => format!("1 {word}"),
        _ if word.ends_with('s') => format!("{count} {word}es"),
        _ if word.ends_with('y') && !word[..word.len() - 1].ends_with(['a', 'e', 'i', 'o', 'u']) => {
            format!("{count} {}ies", &word[..word.len() - 1])
        }
        _ => format!("{count} {word}s"),
    }
}
