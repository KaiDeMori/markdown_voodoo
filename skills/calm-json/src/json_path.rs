use std::iter::Peekable;
use std::str::Chars;

use crate::document::{Document, Step, Value_kind, step_text};
use crate::toc::counted;

const KEY_LIMIT: usize = 10;

pub enum Segment {
    Key(String),
    Index(i64),
}

/// A path such as `hooks.UserPromptSubmit[0]`, or a number such as `@7`, leads to one entry.
pub fn resolve(document: &Document, path_text: &str) -> Result<usize, String> {
    if let Some(number_text) = path_text.strip_prefix('@') {
        return resolve_number(document, path_text, number_text);
    }
    let segments = parse(path_text)?;
    if segments.is_empty() {
        return Err("a path is missing".to_string());
    }
    let mut current = None;
    let mut walked = String::new();
    for segment in &segments {
        let place = if walked.is_empty() { "the root".to_string() } else { walked.clone() };
        let kind = document.kind_at(current).ok_or_else(|| "the file holds no JSON value".to_string())?;
        let children = document.children_of(current);
        let next = match segment {
            Segment::Key(key) => find_key(document, &place, kind, &children, key)?,
            Segment::Index(index) => find_item(&place, kind, &children, *index)?,
        };
        walked.push_str(&segment_text(segment, walked.is_empty()));
        current = Some(next);
    }
    Ok(current.expect("a path has at least one segment"))
}

fn resolve_number(document: &Document, argument: &str, number_text: &str) -> Result<usize, String> {
    let number: usize = number_text.parse().map_err(|_| format!("{argument} is not a number"))?;
    match document.entries.len() {
        0 => Err("nothing to list".to_string()),
        last if (1..=last).contains(&number) => Ok(number - 1),
        last => Err(format!("no {argument}, the last is @{last}")),
    }
}

fn find_key(document: &Document, place: &str, kind: Value_kind, children: &[usize], key: &str) -> Result<usize, String> {
    if kind != Value_kind::Object {
        return Err(wrong_kind(place, kind, children.len()));
    }
    let exact = keyed_children(document, children, |name| name == key);
    match exact.as_slice() {
        [only] => return Ok(*only),
        [] => {}
        _ => {
            let numbers: Vec<String> = exact.iter().map(|&child| format!("@{}", document.entries[child].number)).collect();
            return Err(format!("{key} stands {} times in {place}: {}", exact.len(), numbers.join(", ")));
        }
    }
    let other_case = keyed_children(document, children, |name| name.to_lowercase() == key.to_lowercase());
    if !other_case.is_empty() {
        return Err(format!(
            "no key {key} in {place}, keys are case-sensitive: {}",
            key_list(document, &other_case)
        ));
    }
    if children.is_empty() {
        return Err(format!("no key {key} in {place}; it is empty"));
    }
    Err(format!("no key {key} in {place}; its keys: {}", key_list(document, children)))
}

fn find_item(place: &str, kind: Value_kind, children: &[usize], index: i64) -> Result<usize, String> {
    if kind != Value_kind::Array {
        return Err(wrong_kind(place, kind, children.len()));
    }
    let count = children.len() as i64;
    let position = if index < 0 { count + index } else { index };
    if !(0..count).contains(&position) {
        return Err(format!("no [{index}] in {place}; it has {}", counted(children.len(), "item")));
    }
    Ok(children[position as usize])
}

fn wrong_kind(place: &str, kind: Value_kind, child_count: usize) -> String {
    match kind {
        Value_kind::Object => format!("{place} is an object, so a key comes next, not an index"),
        Value_kind::Array => format!(
            "{place} is an array of {}, so an index comes next, such as [0]",
            counted(child_count, "item")
        ),
        Value_kind::Null => format!("{place} is null, with nothing inside"),
        scalar => format!("{place} is a {}, with nothing inside", scalar.word()),
    }
}

fn keyed_children(document: &Document, children: &[usize], wanted: impl Fn(&str) -> bool) -> Vec<usize> {
    children
        .iter()
        .copied()
        .filter(|&child| match &document.entries[child].step {
            Step::Key(name) => wanted(name),
            Step::Index(_) => false,
        })
        .collect()
}

fn key_list(document: &Document, children: &[usize]) -> String {
    let mut shown: Vec<String> =
        children.iter().take(KEY_LIMIT).map(|&child| step_text(&document.entries[child].step)).collect();
    if children.len() > KEY_LIMIT {
        shown.push(format!("and {} more", children.len() - KEY_LIMIT));
    }
    shown.join(", ")
}

fn segment_text(segment: &Segment, is_first: bool) -> String {
    match segment {
        Segment::Index(index) => format!("[{index}]"),
        Segment::Key(key) if key.contains(['.', '[', ']', '"']) => format!("[\"{key}\"]"),
        Segment::Key(key) if is_first => key.clone(),
        Segment::Key(key) => format!(".{key}"),
    }
}

/// Dots lead to keys and brackets to items; a key in brackets and quotes may hold dots, brackets and spaces.
pub fn parse(text: &str) -> Result<Vec<Segment>, String> {
    let body = text.strip_prefix('$').unwrap_or(text);
    let mut characters = body.chars().peekable();
    let mut segments = Vec::new();
    while let Some(&next) = characters.peek() {
        match next {
            '.' => {
                characters.next();
                segments.push(Segment::Key(take_bare_key(&mut characters, text)?));
            }
            '[' => {
                characters.next();
                segments.push(take_bracket(&mut characters, text)?);
            }
            _ if segments.is_empty() => segments.push(Segment::Key(take_bare_key(&mut characters, text)?)),
            other => return Err(format!("path {text}: a dot or a bracket comes before {other}")),
        }
    }
    Ok(segments)
}

fn take_bare_key(characters: &mut Peekable<Chars>, text: &str) -> Result<String, String> {
    let mut key = String::new();
    while let Some(&next) = characters.peek() {
        match next {
            '.' | '[' => break,
            ']' => return Err(format!("path {text}: a ] without its [")),
            _ => {
                key.push(next);
                characters.next();
            }
        }
    }
    if key.is_empty() {
        return Err(format!("path {text}: a key is empty"));
    }
    Ok(key)
}

/// A quoted key keeps its escapes as written, since keys are compared as they stand in the file.
fn take_bracket(characters: &mut Peekable<Chars>, text: &str) -> Result<Segment, String> {
    if characters.peek() == Some(&'"') {
        characters.next();
        let mut key = String::new();
        loop {
            match characters.next() {
                Some('\\') => {
                    key.push('\\');
                    if let Some(escaped) = characters.next() {
                        key.push(escaped);
                    }
                }
                Some('"') => break,
                Some(other) => key.push(other),
                None => return Err(format!("path {text}: a quoted key misses its closing quote")),
            }
        }
        return match characters.next() {
            Some(']') => Ok(Segment::Key(key)),
            _ => Err(format!("path {text}: a quoted key needs its ] right after the quote")),
        };
    }
    let mut inner = String::new();
    loop {
        match characters.next() {
            Some(']') => break,
            Some(other) => inner.push(other),
            None => return Err(format!("path {text}: a [ without its ]")),
        }
    }
    inner
        .trim()
        .parse::<i64>()
        .map(Segment::Index)
        .map_err(|_| format!("path {text}: [{inner}] is neither an index nor a quoted key"))
}
