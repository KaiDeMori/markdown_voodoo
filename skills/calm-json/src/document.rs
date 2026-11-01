use tree_sitter::{Language, Node, Parser};

use crate::issues;
use crate::toc::counted;

const LABEL_LIMIT: usize = 60;

pub struct Document {
    pub line_count: usize,
    pub root_kind: Option<Value_kind>,
    pub root_summary: Option<String>,
    /// In reading order, each entry directly followed by everything nested inside it.
    pub entries: Vec<Entry>,
}

pub struct Entry {
    pub number: usize,
    pub step: Step,
    pub kind: Value_kind,
    pub label: String,
    pub parent: Option<usize>,
    pub depth: usize,
    pub start_byte: usize,
    pub end_byte: usize,
    pub first_row: usize,
    pub last_row: usize,
}

/// How an entry is reached from the value around it.
pub enum Step {
    Key(String),
    Index(usize),
}

#[derive(Clone, Copy, PartialEq)]
pub enum Value_kind {
    Object,
    Array,
    String,
    Number,
    Boolean,
    Null,
}

impl Value_kind {
    pub fn word(self) -> &'static str {
        match self {
            Value_kind::Object => "object",
            Value_kind::Array => "array",
            Value_kind::String => "string",
            Value_kind::Number => "number",
            Value_kind::Boolean => "boolean",
            Value_kind::Null => "null",
        }
    }

    pub fn is_container(self) -> bool {
        matches!(self, Value_kind::Object | Value_kind::Array)
    }
}

impl Document {
    pub fn descendant_count(&self, index: usize) -> usize {
        let depth = self.entries[index].depth;
        self.entries[index + 1..].iter().take_while(|entry| entry.depth > depth).count()
    }

    pub fn children_of(&self, parent: Option<usize>) -> Vec<usize> {
        (0..self.entries.len()).filter(|&index| self.entries[index].parent == parent).collect()
    }

    /// The root's kind for `None`, an entry's kind otherwise.
    pub fn kind_at(&self, place: Option<usize>) -> Option<Value_kind> {
        match place {
            None => self.root_kind,
            Some(index) => Some(self.entries[index].kind),
        }
    }
}

/// The file is checked first, as calm-md does: one that is not piko bello JSON gets its issues and nothing else.
pub fn build_document(source: &str, allows_comments: bool) -> Result<Document, String> {
    let language: Language = tree_sitter_json::LANGUAGE.into();
    let mut parser = Parser::new();
    parser
        .set_language(&language)
        .map_err(|error| format!("the JSON grammar does not fit this Tree-sitter: {error}"))?;
    let tree = parser.parse(source, None).ok_or_else(|| "the JSON parser gave no tree".to_string())?;
    let found_issues = issues::find_issues(&tree, source, allows_comments);
    if !found_issues.is_empty() {
        return Err(issues::report(&found_issues));
    }
    let document_node = tree.root_node();
    let mut cursor = document_node.walk();
    let root = document_node.named_children(&mut cursor).find(|node| kind_of(*node).is_some());
    let mut entries = Vec::new();
    if let Some(root) = root {
        collect_entries(root, None, 0, source, &mut entries);
    }
    Ok(Document {
        line_count: source.lines().count(),
        root_kind: root.and_then(kind_of),
        root_summary: root.map(|root| cut_to_limit(summary_of(root, source))),
        entries,
    })
}

/// What read returns for an entry, and so what toc weighs.
pub fn entry_text(source: &str, entry: &Entry) -> String {
    if stands_on_own_lines(source, entry) {
        let lines: Vec<&str> =
            source.lines().skip(entry.first_row).take(entry.last_row - entry.first_row + 1).collect();
        lines.join("\n")
    } else {
        source[entry.start_byte..entry.end_byte].to_string()
    }
}

/// A member on lines of its own reads best as whole lines, with its indentation, trailing comma and trailing comment; one inside a line reads as its own slice.
fn stands_on_own_lines(source: &str, entry: &Entry) -> bool {
    let line_start = source[..entry.start_byte].rfind('\n').map_or(0, |position| position + 1);
    let line_end = source[entry.end_byte..].find('\n').map_or(source.len(), |position| entry.end_byte + position);
    let before = &source[line_start..entry.start_byte];
    let after = source[entry.end_byte..line_end].trim();
    let after_comma = after.strip_prefix(',').unwrap_or(after).trim();
    before.trim().is_empty() && (after_comma.is_empty() || after_comma.starts_with("//") || after_comma.starts_with("/*"))
}

fn collect_entries(container: Node, parent: Option<usize>, depth: usize, source: &str, entries: &mut Vec<Entry>) {
    for (step, span, value) in members_of(container, source) {
        let Some(kind) = kind_of(value) else {
            continue;
        };
        let index = entries.len();
        let mut first = span;
        while let Some(comment) = first
            .prev_named_sibling()
            .filter(|sibling| is_attached_comment(*sibling, first))
        {
            first = comment;
        }
        entries.push(Entry {
            number: index + 1,
            label: cut_to_limit(format!("{}: {}", step_text(&step), summary_of(value, source))),
            step,
            kind,
            parent,
            depth,
            start_byte: first.start_byte(),
            end_byte: span.end_byte(),
            first_row: first.start_position().row,
            last_row: last_row_of(span),
        });
        collect_entries(value, Some(index), depth + 1, source, entries);
    }
}

/// Each member with its step, the node that spans it, and its value: a pair spans key and value, an item only itself.
fn members_of<'tree>(container: Node<'tree>, source: &str) -> Vec<(Step, Node<'tree>, Node<'tree>)> {
    let mut cursor = container.walk();
    match container.kind() {
        "object" => container
            .named_children(&mut cursor)
            .filter(|child| child.kind() == "pair")
            .filter_map(|pair| {
                let key = pair.child_by_field_name("key").filter(|key| !key.is_missing())?;
                let value = pair.child_by_field_name("value").filter(|value| !value.is_missing())?;
                Some((Step::Key(key_text(key, source)), pair, value))
            })
            .collect(),
        "array" => container
            .named_children(&mut cursor)
            .filter(|child| kind_of(*child).is_some() && !child.is_missing())
            .enumerate()
            .map(|(index, item)| (Step::Index(index), item, item))
            .collect(),
        _ => Vec::new(),
    }
}

pub fn kind_of(node: Node) -> Option<Value_kind> {
    match node.kind() {
        "object" => Some(Value_kind::Object),
        "array" => Some(Value_kind::Array),
        "string" => Some(Value_kind::String),
        "number" => Some(Value_kind::Number),
        "true" | "false" => Some(Value_kind::Boolean),
        "null" => Some(Value_kind::Null),
        _ => None,
    }
}

/// The key as it stands between its quotes, escapes untouched, so a path matches what the file says.
pub fn key_text(key: Node, source: &str) -> String {
    let text = &source[key.start_byte()..key.end_byte()];
    text.strip_prefix('"').and_then(|inner| inner.strip_suffix('"')).unwrap_or(text).to_string()
}

pub fn step_text(step: &Step) -> String {
    match step {
        Step::Key(key) if key.is_empty() => "\"\"".to_string(),
        Step::Key(key) => key.clone(),
        Step::Index(index) => format!("[{index}]"),
    }
}

fn summary_of(value: Node, source: &str) -> String {
    let members = members_of(value, source);
    match kind_of(value) {
        Some(Value_kind::Object) if members.is_empty() => "object, empty".to_string(),
        Some(Value_kind::Object) => format!("object, {}", counted(members.len(), "key")),
        Some(Value_kind::Array) if members.is_empty() => "array, empty".to_string(),
        Some(Value_kind::Array) => {
            let first_kind = kind_of(members[0].2);
            let item_word = if members.iter().all(|(_, _, item)| kind_of(*item) == first_kind) {
                first_kind.map_or("item", Value_kind::word)
            } else {
                "item"
            };
            format!("array, {}", counted(members.len(), item_word))
        }
        _ => source[value.start_byte()..value.end_byte()].to_string(),
    }
}

fn cut_to_limit(label: String) -> String {
    let length = label.chars().count();
    if length <= LABEL_LIMIT {
        return label;
    }
    let kept: String = label.chars().take(LABEL_LIMIT).collect();
    format!("{kept}... (+{} characters)", length - LABEL_LIMIT)
}

/// A node that ends at the start of a line does not occupy that line.
fn last_row_of(node: Node) -> usize {
    let end = node.end_position();
    if end.column == 0 && end.row > node.start_position().row {
        end.row - 1
    } else {
        end.row
    }
}

/// A comment is attached when it sits on its own lines, directly above what follows, without a blank line in between.
fn is_attached_comment(candidate: Node, following: Node) -> bool {
    candidate.kind() == "comment"
        && last_row_of(candidate) + 1 >= following.start_position().row
        && candidate
            .prev_sibling()
            .is_none_or(|before| last_row_of(before) < candidate.start_position().row)
}
