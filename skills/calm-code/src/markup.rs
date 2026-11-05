use tree_sitter::{Node, Parser};

use crate::languages::{Language_support, language_for_extension};
use crate::outline::{self, Entry, Entry_kind, Outline};

/// Elements that give a page its shape; any element with an id is listed too.
const LANDMARK_TAGS: [&str; 13] =
    ["head", "body", "header", "nav", "main", "section", "article", "aside", "footer", "form", "dialog", "template", "iframe"];
const JAVASCRIPT_TYPES: [&str; 4] = ["", "text/javascript", "application/javascript", "module"];
const ADDRESS_ATTRIBUTES: [&str; 4] = ["href", "src", "action", "formaction"];

struct Attribute {
    name: String,
    value: String,
    text: String,
}

/// What a listed element shows, the names it answers to, and the language its own text is outlined in.
struct Listing {
    kind_word: &'static str,
    tag: String,
    label: String,
    other_names: Vec<String>,
    embedded_extension: Option<&'static str>,
}

struct Page_outline<'source> {
    source: &'source str,
    language_support: &'source Language_support,
    entries: Vec<Entry>,
    syntax_error_count: usize,
}

pub fn build_page_outline(source: &str, language_support: &Language_support) -> Result<Outline, String> {
    let mut parser = Parser::new();
    parser
        .set_language(&language_support.grammar)
        .map_err(|error| format!("the HTML grammar does not fit this Tree-sitter: {error}"))?;
    let tree = parser.parse(source, None).ok_or_else(|| "the HTML parser gave no tree".to_string())?;
    let mut page = Page_outline {
        source,
        language_support,
        entries: Vec::new(),
        syntax_error_count: outline::count_syntax_errors(&tree),
    };
    page.visit(tree.root_node(), None, 0)?;
    for (index, entry) in page.entries.iter_mut().enumerate() {
        entry.number = index + 1;
    }
    Ok(Outline {
        language_name: language_support.name,
        line_count: source.lines().count(),
        entries: page.entries,
        syntax_error_count: page.syntax_error_count,
    })
}

impl Page_outline<'_> {
    /// An element that is not listed passes its children on to the listed element around it.
    fn visit(&mut self, node: Node, parent: Option<usize>, depth: usize) -> Result<(), String> {
        let mut cursor = node.walk();
        let children: Vec<Node> = node.named_children(&mut cursor).collect();
        for child in children {
            let Some(listing) = listing_for(child, self.source) else {
                self.visit(child, parent, depth)?;
                continue;
            };
            let index = self.entries.len();
            let (first_row, last_row) = outline::span_rows(child, self.language_support);
            let last_row = last_row.min(last_content_row(child));
            self.entries.push(Entry {
                number: 0,
                kind: Entry_kind::Container { word: listing.kind_word, holds_methods: false, shows_word: false },
                name: listing.tag,
                other_names: listing.other_names,
                label: outline::cut_to_limit(listing.label),
                parent,
                depth,
                first_row,
                last_row,
            });
            if let Some(extension) = listing.embedded_extension {
                let raw_text = child.named_children(&mut child.walk()).find(|inner| inner.kind() == "raw_text");
                if let Some(raw_text) = raw_text {
                    self.add_embedded_entries(raw_text, extension, index, depth + 1)?;
                }
            }
            self.visit(child, Some(index), depth + 1)?;
        }
        Ok(())
    }

    /// A script or a style is outlined in its own language, over its own range of the page, so its rows stay the page's rows.
    fn add_embedded_entries(&mut self, raw_text: Node, extension: &str, parent: usize, depth: usize) -> Result<(), String> {
        let language_support =
            language_for_extension(extension).ok_or_else(|| format!("no grammar for embedded .{extension}"))?;
        let (embedded_entries, embedded_error_count) =
            outline::build_entries(self.source, &language_support, Some(raw_text.range()))?;
        self.syntax_error_count += embedded_error_count;
        let offset = self.entries.len();
        for mut entry in embedded_entries {
            entry.parent = Some(entry.parent.map_or(parent, |inner| offset + inner));
            entry.depth += depth;
            self.entries.push(entry);
        }
        Ok(())
    }
}

/// An element is listed for its JavaScript first, then for its CSS, then for its place in the page's shape.
fn listing_for(node: Node, source: &str) -> Option<Listing> {
    if !matches!(node.kind(), "element" | "script_element" | "style_element") {
        return None;
    }
    let tag_node = node.named_child(0).filter(|child| matches!(child.kind(), "start_tag" | "self_closing_tag"))?;
    let tag = tag_node
        .named_children(&mut tag_node.walk())
        .find(|child| child.kind() == "tag_name")
        .map(|name| text_of(name, source).to_ascii_lowercase())?;
    let attributes: Vec<Attribute> = tag_node
        .named_children(&mut tag_node.walk())
        .filter(|child| child.kind() == "attribute")
        .map(|attribute| attribute_of(attribute, source))
        .collect();
    let find = |name: &str| attributes.iter().find(|attribute| attribute.name == name);
    let id = find("id");
    let mut shown: Vec<&Attribute> = id.into_iter().collect();
    let mut other_names: Vec<String> = id.iter().flat_map(|id| [id.value.clone(), format!("#{}", id.value)]).collect();
    let (kind_word, embedded_extension) = match node.kind() {
        "script_element" => {
            shown.extend(find("type"));
            shown.extend(find("src"));
            other_names.extend(find("src").map(|src| src.value.clone()));
            let script_type = find("type").map_or(String::new(), |script_type| script_type.value.trim().to_ascii_lowercase());
            let is_javascript = find("src").is_none() && JAVASCRIPT_TYPES.contains(&script_type.as_str());
            ("script", is_javascript.then_some("js"))
        }
        "style_element" => {
            shown.extend(find("media"));
            let is_css = find("type").is_none_or(|style_type| style_type.value.trim().eq_ignore_ascii_case("text/css"));
            ("style", is_css.then_some("css"))
        }
        _ => {
            let is_stylesheet = tag == "link"
                && find("rel").is_some_and(|rel| rel.value.split_whitespace().any(|word| word.eq_ignore_ascii_case("stylesheet")));
            let javascript: Vec<&Attribute> =
                attributes.iter().filter(|attribute| attribute.name.starts_with("on") || is_javascript_address(attribute)).collect();
            if is_stylesheet {
                shown.extend(find("rel"));
                shown.extend(find("href"));
                other_names.extend(find("href").map(|href| href.value.clone()));
                ("stylesheet", None)
            } else if !javascript.is_empty() {
                other_names.extend(javascript.iter().filter(|attribute| attribute.name.starts_with("on")).map(|handler| handler.name.clone()));
                shown.extend(javascript);
                ("handler", None)
            } else if let Some(style) = find("style") {
                shown.push(style);
                ("inline style", None)
            } else if id.is_some() || LANDMARK_TAGS.contains(&tag.as_str()) {
                ("element", None)
            } else {
                return None;
            }
        }
    };
    let shown_text: String = shown.iter().map(|attribute| format!(" {}", attribute.text)).collect();
    Some(Listing { kind_word, label: format!("<{tag}{shown_text}>"), tag, other_names, embedded_extension })
}

/// An element without an end tag, such as `<link>`, runs on to whatever follows; its own content ends with its last child.
fn last_content_row(element: Node) -> usize {
    let has_end_tag = element.named_children(&mut element.walk()).any(|child| child.kind() == "end_tag");
    match element.named_child(element.named_child_count().saturating_sub(1) as u32) {
        Some(last_child) if !has_end_tag => last_child.end_position().row,
        _ => element.end_position().row,
    }
}

fn is_javascript_address(attribute: &Attribute) -> bool {
    ADDRESS_ATTRIBUTES.contains(&attribute.name.as_str())
        && attribute.value.trim_start().to_ascii_lowercase().starts_with("javascript:")
}

fn attribute_of(attribute: Node, source: &str) -> Attribute {
    let mut name = String::new();
    let mut value = String::new();
    for child in attribute.named_children(&mut attribute.walk()) {
        match child.kind() {
            "attribute_name" => name = text_of(child, source).to_ascii_lowercase(),
            "attribute_value" => value = text_of(child, source).to_string(),
            "quoted_attribute_value" => {
                value = child.named_child(0).map(|inner| text_of(inner, source).to_string()).unwrap_or_default();
            }
            _ => {}
        }
    }
    Attribute { name, value, text: outline::flatten_whitespace(text_of(attribute, source)) }
}

fn text_of<'source>(node: Node, source: &'source str) -> &'source str {
    &source[node.start_byte()..node.end_byte()]
}
