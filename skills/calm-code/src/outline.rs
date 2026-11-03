use std::cmp::Reverse;
use std::collections::{HashMap, HashSet};

use tree_sitter::{Node, Parser, Query, QueryCursor, StreamingIterator, Tree};

use crate::languages::Language_support;

const LABEL_LIMIT: usize = 60;
const CANDIDATE_LIMIT: usize = 10;

pub struct Outline {
    pub language_name: &'static str,
    pub line_count: usize,
    /// In reading order, each entry directly followed by everything nested inside it.
    pub entries: Vec<Entry>,
    pub syntax_error_count: usize,
}

pub struct Entry {
    pub number: usize,
    pub kind: Entry_kind,
    pub name: String,
    pub second_name: Option<String>,
    pub label: String,
    pub parent: Option<usize>,
    pub depth: usize,
    pub first_row: usize,
    pub last_row: usize,
}

#[derive(Clone, Copy)]
pub enum Entry_kind {
    Container { word: &'static str, holds_methods: bool },
    Method,
    Function,
    Property,
}

enum Definition_kind {
    Container { word: &'static str, holds_methods: bool },
    Callable,
    Property,
}

struct Definition<'tree> {
    node: Node<'tree>,
    kind: Definition_kind,
    name: String,
    second_name: Option<String>,
    prefix: Option<String>,
    parameters: Option<String>,
    label_text: Option<String>,
}

enum Enclosing {
    Top_level,
    Listed { index: usize, is_direct: bool },
    Left_out,
}

impl Entry {
    pub fn kind_word(&self) -> &'static str {
        match self.kind {
            Entry_kind::Container { word, .. } => word,
            Entry_kind::Method => "method",
            Entry_kind::Function => "function",
            Entry_kind::Property => "property",
        }
    }

    pub fn is_container(&self) -> bool {
        matches!(self.kind, Entry_kind::Container { .. })
    }

    pub fn holds_methods(&self) -> bool {
        matches!(self.kind, Entry_kind::Container { holds_methods: true, .. })
    }

    pub fn names(&self) -> impl Iterator<Item = &str> {
        std::iter::once(self.name.as_str()).chain(self.second_name.as_deref())
    }

    pub fn line_count(&self) -> usize {
        self.last_row - self.first_row + 1
    }
}

impl Outline {
    pub fn descendant_count(&self, index: usize) -> usize {
        let depth = self.entries[index].depth;
        self.entries[index + 1..].iter().take_while(|entry| entry.depth > depth).count()
    }

    pub fn children_of(&self, parent: Option<usize>) -> Vec<usize> {
        (0..self.entries.len()).filter(|&index| self.entries[index].parent == parent).collect()
    }

    /// A name path ends with the entry's own name and needs only as many enclosing names as it takes to be unique.
    pub fn resolve(&self, name_path: &[String], prefer_containers: bool) -> Result<usize, String> {
        if let [single] = name_path {
            if let Some(number_text) = single.strip_prefix('@') {
                return self.resolve_number(single, number_text);
            }
        }
        let Some((target_name, enclosing_names)) = name_path.split_last() else {
            return Err("a name is missing".to_string());
        };
        let mut candidates = self.matching_entries(target_name, enclosing_names, true);
        if candidates.is_empty() {
            let other_case = self.matching_entries(target_name, enclosing_names, false);
            return Err(if other_case.is_empty() {
                format!("nothing named {}", name_path.join(" "))
            } else {
                format!(
                    "nothing named {}, names are case-sensitive: {}",
                    name_path.join(" "),
                    self.candidate_list(&other_case)
                )
            });
        }
        if prefer_containers && candidates.iter().any(|&index| self.entries[index].is_container()) {
            candidates.retain(|&index| self.entries[index].is_container());
        }
        match candidates.as_slice() {
            [only] => Ok(*only),
            _ => Err(format!(
                "{} fits {} entries: {}",
                name_path.join(" "),
                candidates.len(),
                self.candidate_list(&candidates)
            )),
        }
    }

    fn resolve_number(&self, argument: &str, number_text: &str) -> Result<usize, String> {
        let number: usize = number_text.parse().map_err(|_| format!("{argument} is not a number"))?;
        match self.entries.len() {
            0 => Err("nothing to list".to_string()),
            last if (1..=last).contains(&number) => Ok(number - 1),
            last => Err(format!("no {argument}, the last is @{last}")),
        }
    }

    /// The enclosing names are taken in order by the entries around the target, from the outermost, and then by the target's other name.
    /// An entry takes the next name while one of its names not taken yet matches it, so its two names may come in either order.
    fn matching_entries(&self, target_name: &str, enclosing_names: &[String], case_sensitive: bool) -> Vec<usize> {
        let names_match = |name: &str, wanted: &str| {
            if case_sensitive { name == wanted } else { name.to_lowercase() == wanted.to_lowercase() }
        };
        (0..self.entries.len())
            .filter(|&index| {
                let entry = &self.entries[index];
                let Some(target_position) = entry.names().position(|name| names_match(name, target_name)) else {
                    return false;
                };
                let mut name_groups: Vec<Vec<&str>> = self
                    .enclosing_entries(index)
                    .into_iter()
                    .map(|enclosing| self.entries[enclosing].names().collect())
                    .collect();
                name_groups.push(
                    entry.names().enumerate().filter(|&(position, _)| position != target_position).map(|(_, name)| name).collect(),
                );
                let mut wanted = enclosing_names.iter().peekable();
                for mut available_names in name_groups {
                    while let Some(position) = wanted
                        .peek()
                        .and_then(|wanted_name| available_names.iter().position(|name| names_match(name, wanted_name)))
                    {
                        available_names.remove(position);
                        wanted.next();
                    }
                }
                wanted.peek().is_none()
            })
            .collect()
    }

    /// From the outermost to the innermost.
    fn enclosing_entries(&self, index: usize) -> Vec<usize> {
        let mut enclosing = Vec::new();
        let mut current = self.entries[index].parent;
        while let Some(parent_index) = current {
            enclosing.push(parent_index);
            current = self.entries[parent_index].parent;
        }
        enclosing.reverse();
        enclosing
    }

    /// The enclosing names in front tell apart candidates whose labels are equal.
    fn candidate_list(&self, candidates: &[usize]) -> String {
        let mut shown: Vec<String> = candidates
            .iter()
            .take(CANDIDATE_LIMIT)
            .map(|&index| {
                let mut parts: Vec<&str> =
                    self.enclosing_entries(index).into_iter().flat_map(|enclosing| self.entries[enclosing].names()).collect();
                parts.push(&self.entries[index].label);
                format!("@{} {}", self.entries[index].number, parts.join(" "))
            })
            .collect();
        if candidates.len() > CANDIDATE_LIMIT {
            shown.push(format!("and {} more", candidates.len() - CANDIDATE_LIMIT));
        }
        shown.join(", ")
    }
}

pub fn build_outline(source: &str, language_support: &Language_support) -> Result<Outline, String> {
    let language_name = language_support.name;
    let mut parser = Parser::new();
    parser
        .set_language(&language_support.grammar)
        .map_err(|error| format!("the {language_name} grammar does not fit this Tree-sitter: {error}"))?;
    let tree = parser
        .parse(source, None)
        .ok_or_else(|| format!("the {language_name} parser gave no tree"))?;
    let query = Query::new(&language_support.grammar, language_support.definitions_query)
        .map_err(|error| format!("the {language_name} query is broken: {error}"))?;
    let definitions = collect_definitions(&tree, &query, source, language_support);
    Ok(Outline {
        language_name,
        line_count: source.lines().count(),
        entries: nest_definitions(definitions, language_support),
        syntax_error_count: count_syntax_errors(&tree),
    })
}

fn collect_definitions<'tree>(
    tree: &'tree Tree,
    query: &Query,
    source: &str,
    language_support: &Language_support,
) -> Vec<Definition<'tree>> {
    let capture_names = query.capture_names();
    let mut cursor = QueryCursor::new();
    let mut matches = cursor.matches(query, tree.root_node(), source.as_bytes());
    let mut seen_nodes = HashSet::new();
    let mut definitions = Vec::new();
    while let Some(query_match) = matches.next() {
        let mut definition = None;
        let mut name = None;
        let mut second_name = None;
        let mut prefix = None;
        let mut parameters = None;
        let mut label_span: Option<std::ops::Range<usize>> = None;
        for capture in query_match.captures() {
            let text = capture.node.utf8_text(source.as_bytes()).unwrap_or_default();
            match capture_names[capture.index as usize] {
                "name" => name = Some(name_text(capture.node, source, language_support)),
                "second_name" => second_name = Some(name_text(capture.node, source, language_support)),
                "prefix" => prefix = Some(text.to_string()),
                "parameters" => {
                    let text = text_without_comments(capture.node, capture.node.byte_range(), source, language_support);
                    parameters = Some(flatten_parameters(&text));
                }
                "label" => {
                    let range = capture.node.byte_range();
                    label_span = Some(match label_span {
                        Some(span) => span.start.min(range.start)..span.end.max(range.end),
                        None => range,
                    });
                }
                capture_name => {
                    if let Some(kind) = definition_kind_for(capture_name) {
                        definition = Some((capture.node, kind));
                    }
                }
            }
        }
        if let (Some((node, kind)), Some(name)) = (definition, name) {
            if seen_nodes.insert(node.id()) {
                let label_text = label_span
                    .map(|span| flatten_whitespace(&text_without_comments(node, span, source, language_support)));
                definitions.push(Definition { node, kind, name, second_name, prefix, parameters, label_text });
            }
        }
    }
    definitions.sort_by_key(|definition| (definition.node.start_byte(), Reverse(definition.node.end_byte())));
    definitions
}

/// A name capture leads down the language's name fields to the node that names it.
fn name_text(node: Node, source: &str, language_support: &Language_support) -> String {
    let mut named = node;
    while let Some(inner) = language_support.name_fields.iter().find_map(|field| named.child_by_field_name(field)) {
        named = inner;
    }
    named.utf8_text(source.as_bytes()).unwrap_or_default().to_string()
}

fn definition_kind_for(capture_name: &str) -> Option<Definition_kind> {
    let (word, holds_methods) = match capture_name.strip_prefix("definition.")? {
        "method" | "constructor" | "function" => return Some(Definition_kind::Callable),
        "property" => return Some(Definition_kind::Property),
        "class" => ("class", true),
        "struct" => ("struct", true),
        "enum" => ("enum", true),
        "interface" => ("interface", true),
        "trait" => ("trait", true),
        "record" => ("record", true),
        "type" => ("type", true),
        "impl" => ("impl", true),
        "mod" => ("mod", false),
        "macro" => ("macro", false),
        _ => return None,
    };
    Some(Definition_kind::Container { word, holds_methods })
}

fn nest_definitions(definitions: Vec<Definition>, language_support: &Language_support) -> Vec<Entry> {
    let mut entry_index_by_node: HashMap<usize, Option<usize>> = HashMap::new();
    let mut entries: Vec<Entry> = Vec::new();
    for definition in definitions {
        let parent = match enclosing_definition(definition.node, &entry_index_by_node, language_support) {
            Enclosing::Top_level => None,
            Enclosing::Listed { index, is_direct } if is_direct || entries[index].is_container() => Some(index),
            Enclosing::Listed { .. } | Enclosing::Left_out => {
                entry_index_by_node.insert(definition.node.id(), None);
                continue;
            }
        };
        let kind = match definition.kind {
            Definition_kind::Container { word, holds_methods } => Entry_kind::Container { word, holds_methods },
            Definition_kind::Callable if parent.is_some_and(|index| entries[index].holds_methods()) => {
                Entry_kind::Method
            }
            Definition_kind::Callable => Entry_kind::Function,
            Definition_kind::Property => Entry_kind::Property,
        };
        let label = label_for(
            kind,
            definition.prefix.as_deref(),
            &definition.name,
            definition.parameters.as_deref(),
            definition.label_text.as_deref(),
        );
        let depth = parent.map_or(0, |index| entries[index].depth + 1);
        let (first_row, last_row) = span_rows(definition.node, language_support);
        entry_index_by_node.insert(definition.node.id(), Some(entries.len()));
        entries.push(Entry {
            number: entries.len() + 1,
            kind,
            name: definition.name,
            second_name: definition.second_name,
            label,
            parent,
            depth,
            first_row,
            last_row,
        });
    }
    entries
}

/// A definition is direct when only body kinds stand between it and the definition around it.
fn enclosing_definition(
    node: Node,
    entry_index_by_node: &HashMap<usize, Option<usize>>,
    language_support: &Language_support,
) -> Enclosing {
    let mut is_direct = true;
    let mut ancestor = outer_node(node, language_support).parent();
    while let Some(current) = ancestor {
        match entry_index_by_node.get(&current.id()) {
            Some(Some(index)) => return Enclosing::Listed { index: *index, is_direct },
            Some(None) => return Enclosing::Left_out,
            None => {
                is_direct &= language_support.body_kinds.contains(&current.kind());
                ancestor = current.parent();
            }
        }
    }
    Enclosing::Top_level
}

fn outer_node<'tree>(definition_node: Node<'tree>, language_support: &Language_support) -> Node<'tree> {
    let mut outer = definition_node;
    while let Some(wrapper) = outer
        .parent()
        .filter(|parent| language_support.wrapper_kinds.contains(&parent.kind()))
    {
        outer = wrapper;
    }
    outer
}

/// The span reaches up over wrappers and back over attached comments, so it holds everything a reader needs.
/// Some grammars, TypeScript's among them, place a member's decorators beside it instead of inside it.
fn span_rows(definition_node: Node, language_support: &Language_support) -> (usize, usize) {
    let outer = outer_node(definition_node, language_support);
    let mut first = outer;
    while let Some(leading) = first.prev_named_sibling().filter(|sibling| {
        language_support.leading_kinds.contains(&sibling.kind()) || is_attached_comment(*sibling, first, language_support)
    }) {
        first = leading;
    }
    (first.start_position().row, last_row_of(outer))
}

/// A comment is attached when it sits on its own lines, directly above what follows, without a blank line in between.
/// A comment that documents what surrounds it is never attached.
fn is_attached_comment(candidate: Node, following: Node, language_support: &Language_support) -> bool {
    language_support.comment_kinds.contains(&candidate.kind())
        && !holds_inner_comment_marker(candidate, language_support)
        && last_row_of(candidate) + 1 >= following.start_position().row
        && candidate
            .prev_sibling()
            .is_none_or(|before| last_row_of(before) < candidate.start_position().row)
}

fn holds_inner_comment_marker(comment: Node, language_support: &Language_support) -> bool {
    let mut cursor = comment.walk();
    comment.children(&mut cursor).any(|child| language_support.inner_comment_markers.contains(&child.kind()))
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

/// A label text stands where the name would, for a definition that its header shows better than its name.
fn label_for(
    kind: Entry_kind,
    prefix: Option<&str>,
    name: &str,
    parameters: Option<&str>,
    label_text: Option<&str>,
) -> String {
    let name = match (label_text, prefix) {
        (Some(label_text), _) => label_text.to_string(),
        (None, Some(prefix)) => format!("{prefix} {name}"),
        (None, None) => name.to_string(),
    };
    let label = match (kind, parameters) {
        (Entry_kind::Container { word, .. }, _) => format!("{word} {name}"),
        (Entry_kind::Property, _) => format!("property {name}"),
        (_, Some(parameters)) if parameters.starts_with('(') => format!("{name}{parameters}"),
        (_, Some(parameters)) => format!("{name}({parameters})"),
        (_, None) => format!("{name}()"),
    };
    cut_to_limit(label)
}

/// A comment inside a parameter list or a label text would read as if it swallowed what follows it.
fn text_without_comments(
    node: Node,
    span: std::ops::Range<usize>,
    source: &str,
    language_support: &Language_support,
) -> String {
    let mut comment_ranges = Vec::new();
    collect_comment_ranges(node, language_support.comment_kinds, &mut comment_ranges);
    let mut text = String::new();
    let mut position = span.start;
    for range in comment_ranges.into_iter().filter(|range| span.start <= range.start && range.end <= span.end) {
        text.push_str(&source[position..range.start]);
        text.push(' ');
        position = range.end;
    }
    text.push_str(&source[position..span.end]);
    text
}

fn collect_comment_ranges(node: Node, comment_kinds: &[&str], comment_ranges: &mut Vec<std::ops::Range<usize>>) {
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if comment_kinds.contains(&child.kind()) {
            comment_ranges.push(child.start_byte()..child.end_byte());
        } else {
            collect_comment_ranges(child, comment_kinds, comment_ranges);
        }
    }
}

fn flatten_whitespace(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Only the comma right before the closing parenthesis goes, so a tuple such as `(1,)` inside keeps its meaning.
fn flatten_parameters(text: &str) -> String {
    let flat = flatten_whitespace(text).replace("( ", "(").replace(" )", ")");
    match flat.strip_suffix(",)") {
        Some(without_trailing_comma) => format!("{without_trailing_comma})"),
        None => flat,
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

fn count_syntax_errors(tree: &Tree) -> usize {
    let mut cursor = tree.walk();
    let mut count = 0;
    loop {
        let node = cursor.node();
        if node.is_error() || node.is_missing() {
            count += 1;
        } else if node.has_error() && cursor.goto_first_child() {
            continue;
        }
        loop {
            if cursor.goto_next_sibling() {
                break;
            }
            if !cursor.goto_parent() {
                return count;
            }
        }
    }
}
