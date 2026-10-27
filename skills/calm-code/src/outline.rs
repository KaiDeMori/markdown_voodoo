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
    pub label: String,
    pub parent: Option<usize>,
    pub depth: usize,
    pub first_row: usize,
    pub last_row: usize,
}

#[derive(Clone, Copy)]
pub enum Entry_kind {
    Container(&'static str),
    Method,
    Function,
    Property,
}

enum Definition_kind {
    Container(&'static str),
    Callable,
    Property,
}

struct Definition<'tree> {
    node: Node<'tree>,
    kind: Definition_kind,
    name: String,
    prefix: Option<String>,
    parameters: Option<String>,
}

enum Enclosing {
    Top_level,
    Listed { index: usize, is_direct: bool },
    Left_out,
}

impl Entry {
    pub fn kind_word(&self) -> &'static str {
        match self.kind {
            Entry_kind::Container(word) => word,
            Entry_kind::Method => "method",
            Entry_kind::Function => "function",
            Entry_kind::Property => "property",
        }
    }

    pub fn is_container(&self) -> bool {
        matches!(self.kind, Entry_kind::Container(_))
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

    fn matching_entries(&self, target_name: &str, enclosing_names: &[String], case_sensitive: bool) -> Vec<usize> {
        let names_match = |name: &str, wanted: &str| {
            if case_sensitive { name == wanted } else { name.to_lowercase() == wanted.to_lowercase() }
        };
        (0..self.entries.len())
            .filter(|&index| names_match(&self.entries[index].name, target_name))
            .filter(|&index| {
                let mut wanted = enclosing_names.iter().peekable();
                for name in self.enclosing_names(index) {
                    if wanted.peek().is_some_and(|wanted_name| names_match(name, wanted_name)) {
                        wanted.next();
                    }
                }
                wanted.peek().is_none()
            })
            .collect()
    }

    /// From the outermost to the innermost.
    fn enclosing_names(&self, index: usize) -> Vec<&str> {
        let mut names = Vec::new();
        let mut current = self.entries[index].parent;
        while let Some(parent_index) = current {
            names.push(self.entries[parent_index].name.as_str());
            current = self.entries[parent_index].parent;
        }
        names.reverse();
        names
    }

    /// The enclosing names in front tell apart candidates whose labels are equal.
    fn candidate_list(&self, candidates: &[usize]) -> String {
        let mut shown: Vec<String> = candidates
            .iter()
            .take(CANDIDATE_LIMIT)
            .map(|&index| {
                let mut parts = self.enclosing_names(index);
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
    let definitions = collect_definitions(&tree, &query, source);
    Ok(Outline {
        language_name,
        line_count: source.lines().count(),
        entries: nest_definitions(definitions, language_support),
        syntax_error_count: count_syntax_errors(&tree),
    })
}

fn collect_definitions<'tree>(tree: &'tree Tree, query: &Query, source: &str) -> Vec<Definition<'tree>> {
    let capture_names = query.capture_names();
    let mut cursor = QueryCursor::new();
    let mut matches = cursor.matches(query, tree.root_node(), source.as_bytes());
    let mut seen_nodes = HashSet::new();
    let mut definitions = Vec::new();
    while let Some(query_match) = matches.next() {
        let mut definition = None;
        let mut name = None;
        let mut prefix = None;
        let mut parameters = None;
        for capture in query_match.captures() {
            let text = capture.node.utf8_text(source.as_bytes()).unwrap_or_default();
            match capture_names[capture.index as usize] {
                "name" => name = Some(text.to_string()),
                "prefix" => prefix = Some(text.to_string()),
                "parameters" => parameters = Some(flatten_parameters(&text_without_comments(capture.node, source))),
                capture_name => {
                    if let Some(kind) = definition_kind_for(capture_name) {
                        definition = Some((capture.node, kind));
                    }
                }
            }
        }
        if let (Some((node, kind)), Some(name)) = (definition, name) {
            if seen_nodes.insert(node.id()) {
                definitions.push(Definition { node, kind, name, prefix, parameters });
            }
        }
    }
    definitions.sort_by_key(|definition| (definition.node.start_byte(), Reverse(definition.node.end_byte())));
    definitions
}

fn definition_kind_for(capture_name: &str) -> Option<Definition_kind> {
    let kind = match capture_name.strip_prefix("definition.")? {
        "class" => Definition_kind::Container("class"),
        "struct" => Definition_kind::Container("struct"),
        "interface" => Definition_kind::Container("interface"),
        "record" => Definition_kind::Container("record"),
        "method" | "constructor" | "function" => Definition_kind::Callable,
        "property" => Definition_kind::Property,
        _ => return None,
    };
    Some(kind)
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
            Definition_kind::Container(word) => Entry_kind::Container(word),
            Definition_kind::Callable if parent.is_some_and(|index| entries[index].is_container()) => {
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
        );
        let depth = parent.map_or(0, |index| entries[index].depth + 1);
        let (first_row, last_row) = span_rows(definition.node, language_support);
        entry_index_by_node.insert(definition.node.id(), Some(entries.len()));
        entries.push(Entry {
            number: entries.len() + 1,
            kind,
            name: definition.name,
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
fn span_rows(definition_node: Node, language_support: &Language_support) -> (usize, usize) {
    let outer = outer_node(definition_node, language_support);
    let mut first = outer;
    while let Some(comment) = first
        .prev_named_sibling()
        .filter(|sibling| is_attached_comment(*sibling, first))
    {
        first = comment;
    }
    (first.start_position().row, last_row_of(outer))
}

/// A comment is attached when it sits on its own lines, directly above what follows, without a blank line in between.
fn is_attached_comment(candidate: Node, following: Node) -> bool {
    candidate.kind() == "comment"
        && last_row_of(candidate) + 1 >= following.start_position().row
        && candidate
            .prev_sibling()
            .is_none_or(|before| last_row_of(before) < candidate.start_position().row)
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

fn label_for(kind: Entry_kind, prefix: Option<&str>, name: &str, parameters: Option<&str>) -> String {
    let name = match prefix {
        Some(prefix) => format!("{prefix} {name}"),
        None => name.to_string(),
    };
    let label = match (kind, parameters) {
        (Entry_kind::Container(word), _) => format!("{word} {name}"),
        (Entry_kind::Property, _) => format!("property {name}"),
        (_, Some(parameters)) if parameters.starts_with('(') => format!("{name}{parameters}"),
        (_, Some(parameters)) => format!("{name}({parameters})"),
        (_, None) => format!("{name}()"),
    };
    cut_to_limit(label)
}

/// A comment inside a parameter list would read as if it swallowed the parameters after it.
fn text_without_comments(node: Node, source: &str) -> String {
    let mut comment_ranges = Vec::new();
    collect_comment_ranges(node, &mut comment_ranges);
    let mut text = String::new();
    let mut position = node.start_byte();
    for range in comment_ranges {
        text.push_str(&source[position..range.start]);
        text.push(' ');
        position = range.end;
    }
    text.push_str(&source[position..node.end_byte()]);
    text
}

fn collect_comment_ranges(node: Node, comment_ranges: &mut Vec<std::ops::Range<usize>>) {
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if child.kind() == "comment" {
            comment_ranges.push(child.start_byte()..child.end_byte());
        } else {
            collect_comment_ranges(child, comment_ranges);
        }
    }
}

/// Only the comma right before the closing parenthesis goes, so a tuple such as `(1,)` inside keeps its meaning.
fn flatten_parameters(text: &str) -> String {
    let flat = text.split_whitespace().collect::<Vec<_>>().join(" ").replace("( ", "(").replace(" )", ")");
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
