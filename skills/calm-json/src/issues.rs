use std::collections::HashSet;

use tree_sitter::{Node, Tree};

use crate::document::{key_text, kind_of};
use crate::toc::counted;

const ISSUE_LIMIT: usize = 10;
const EXCERPT_LIMIT: usize = 30;

/// Every way the file falls short of piko bello JSON, each with its row, in reading order.
pub fn find_issues(tree: &Tree, source: &str, allows_comments: bool) -> Vec<(usize, String)> {
    let mut issues = Vec::new();
    let mut cursor = tree.walk();
    'walk: loop {
        let node = cursor.node();
        let is_broken = node.is_error() || node.is_missing();
        if is_broken {
            issues.push(syntax_issue(node, source));
        } else if node.kind() == "comment" && !allows_comments {
            issues.push((
                node.start_position().row,
                "a comment, which JSON does not hold; a .jsonc file may".to_string(),
            ));
        } else if node.kind() == "object" {
            issues.extend(duplicate_keys(node, source));
        }
        if !is_broken && cursor.goto_first_child() {
            continue;
        }
        loop {
            if cursor.goto_next_sibling() {
                break;
            }
            if !cursor.goto_parent() {
                break 'walk;
            }
        }
    }
    issues.extend(top_level_issue(tree.root_node()));
    issues.sort_by_key(|(row, _)| *row);
    issues
}

pub fn report(issues: &[(usize, String)]) -> String {
    let fix = if issues.len() == 1 { "fix it" } else { "fix them" };
    let mut lines = vec![format!("{}, {fix} and call again:", counted(issues.len(), "issue"))];
    lines.extend(issues.iter().take(ISSUE_LIMIT).map(|(row, text)| format!("line {}: {text}", row + 1)));
    if issues.len() > ISSUE_LIMIT {
        lines.push(format!("and {} more", issues.len() - ISSUE_LIMIT));
    }
    lines.join("\n")
}

/// An error often starts at the comma before the trouble, while its first named child stands where the trouble is.
fn syntax_issue(node: Node, source: &str) -> (usize, String) {
    if let Some((comma_row, closing)) = trailing_comma(node, source) {
        return (comma_row, format!("a trailing comma before {closing}, which JSON does not hold"));
    }
    if node.is_missing() {
        return (node.start_position().row, format!("missing {}", node.kind()));
    }
    let start = node.named_child(0).unwrap_or(node);
    let text = source[start.start_byte()..node.end_byte()].split_whitespace().collect::<Vec<_>>().join(" ");
    let excerpt = if text.chars().count() > EXCERPT_LIMIT {
        format!("{}...", text.chars().take(EXCERPT_LIMIT).collect::<String>())
    } else {
        text
    };
    (start.start_position().row, format!("syntax error at {excerpt}"))
}

/// The grammar sees a trailing comma as a missing item in an array, and as an error holding the comma in an object.
fn trailing_comma(node: Node, source: &str) -> Option<(usize, &'static str)> {
    let closing = match sibling_beside_comments(node, Node::next_sibling)?.kind() {
        "]" => "]",
        "}" => "}",
        _ => return None,
    };
    if node.is_missing() {
        let comma = sibling_beside_comments(node, Node::prev_sibling).filter(|previous| previous.kind() == ",")?;
        return Some((comma.start_position().row, closing));
    }
    (node.is_error() && source[node.start_byte()..node.end_byte()].trim() == ",")
        .then(|| (node.start_position().row, closing))
}

fn sibling_beside_comments<'tree>(node: Node<'tree>, step: fn(&Node<'tree>) -> Option<Node<'tree>>) -> Option<Node<'tree>> {
    let mut sibling = step(&node);
    while let Some(current) = sibling.filter(|current| current.kind() == "comment") {
        sibling = step(&current);
    }
    sibling
}

fn duplicate_keys(object: Node, source: &str) -> Vec<(usize, String)> {
    let mut seen = HashSet::new();
    let mut cursor = object.walk();
    object
        .named_children(&mut cursor)
        .filter(|child| child.kind() == "pair")
        .filter_map(|pair| pair.child_by_field_name("key"))
        .filter_map(|key| {
            let text = key_text(key, source);
            (!seen.insert(text.clone()))
                .then(|| (key.start_position().row, format!("the key \"{text}\" stands twice in one object")))
        })
        .collect()
}

fn top_level_issue(document: Node) -> Option<(usize, String)> {
    let mut cursor = document.walk();
    let values: Vec<Node> = document.named_children(&mut cursor).filter(|node| kind_of(*node).is_some()).collect();
    match values.as_slice() {
        [] => Some((0, "no JSON value in the file".to_string())),
        [_] => None,
        [_, second, ..] => Some((
            second.start_position().row,
            "a second value at the top, while JSON holds one".to_string(),
        )),
    }
}
