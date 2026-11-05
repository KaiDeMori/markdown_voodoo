use std::path::Path;

use tree_sitter::Language;

pub struct Language_support {
    pub name: &'static str,
    pub grammar: Language,
    pub definitions_query: &'static str,
    /// Nodes of these kinds wrap a definition and belong to it, so decorators and export keywords travel with it.
    pub wrapper_kinds: &'static [&'static str],
    /// Nodes of these kinds may stand between a function and a definition directly in its body, which then counts as its child.
    pub body_kinds: &'static [&'static str],
    /// Nodes of these kinds stand beside a definition, in front of it, and belong to it, such as decorators and attributes.
    pub leading_kinds: &'static [&'static str],
    pub comment_kinds: &'static [&'static str],
    /// A comment holding a node of one of these kinds documents what surrounds it, so it never travels with the definition below.
    pub inner_comment_markers: &'static [&'static str],
    /// A captured name follows these fields down to the node that names it, so a reference or a generic type answers to its type's own name.
    pub name_fields: &'static [&'static str],
}

pub fn language_for(path: &Path) -> Option<Language_support> {
    language_for_extension(&path.extension()?.to_str()?.to_ascii_lowercase())
}

pub fn language_for_extension(extension: &str) -> Option<Language_support> {
    let language_support = match extension {
        "cs" => Language_support {
            name: "C#",
            grammar: tree_sitter_c_sharp::LANGUAGE.into(),
            definitions_query: include_str!("queries/c_sharp.scm"),
            wrapper_kinds: &[],
            body_kinds: &[],
            leading_kinds: &["decorator"],
            comment_kinds: &["comment"],
            inner_comment_markers: &[],
            name_fields: &[],
        },
        "py" | "pyw" => Language_support {
            name: "Python",
            grammar: tree_sitter_python::LANGUAGE.into(),
            definitions_query: include_str!("queries/python.scm"),
            wrapper_kinds: &["decorated_definition"],
            body_kinds: &["block"],
            leading_kinds: &["decorator"],
            comment_kinds: &["comment"],
            inner_comment_markers: &[],
            name_fields: &[],
        },
        "js" | "mjs" | "cjs" | "jsx" => Language_support {
            name: "JavaScript",
            grammar: tree_sitter_javascript::LANGUAGE.into(),
            definitions_query: include_str!("queries/javascript.scm"),
            wrapper_kinds: &["export_statement", "lexical_declaration", "variable_declaration"],
            body_kinds: &["statement_block", "arrow_function", "function_expression", "generator_function"],
            leading_kinds: &["decorator"],
            comment_kinds: &["comment"],
            inner_comment_markers: &[],
            name_fields: &[],
        },
        "ts" | "mts" | "cts" => Language_support {
            name: "TypeScript",
            grammar: tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into(),
            definitions_query: include_str!("queries/typescript.scm"),
            wrapper_kinds: &["export_statement", "lexical_declaration", "variable_declaration"],
            body_kinds: &["statement_block", "arrow_function", "function_expression", "generator_function"],
            leading_kinds: &["decorator"],
            comment_kinds: &["comment"],
            inner_comment_markers: &[],
            name_fields: &[],
        },
        "tsx" => Language_support {
            name: "TypeScript",
            grammar: tree_sitter_typescript::LANGUAGE_TSX.into(),
            definitions_query: include_str!("queries/typescript.scm"),
            wrapper_kinds: &["export_statement", "lexical_declaration", "variable_declaration"],
            body_kinds: &["statement_block", "arrow_function", "function_expression", "generator_function"],
            leading_kinds: &["decorator"],
            comment_kinds: &["comment"],
            inner_comment_markers: &[],
            name_fields: &[],
        },
        "rs" => Language_support {
            name: "Rust",
            grammar: tree_sitter_rust::LANGUAGE.into(),
            definitions_query: include_str!("queries/rust.scm"),
            wrapper_kinds: &[],
            body_kinds: &["block"],
            leading_kinds: &["attribute_item"],
            comment_kinds: &["line_comment", "block_comment"],
            inner_comment_markers: &["inner_doc_comment_marker"],
            name_fields: &["type", "name", "trait"],
        },
        "css" => Language_support {
            name: "CSS",
            grammar: tree_sitter_css::LANGUAGE.into(),
            definitions_query: include_str!("queries/css.scm"),
            wrapper_kinds: &[],
            body_kinds: &[],
            leading_kinds: &[],
            comment_kinds: &["comment", "js_comment"],
            inner_comment_markers: &[],
            name_fields: &[],
        },
        "html" | "htm" => Language_support {
            name: "HTML",
            grammar: tree_sitter_html::LANGUAGE.into(),
            definitions_query: "",
            wrapper_kinds: &[],
            body_kinds: &[],
            leading_kinds: &[],
            comment_kinds: &["comment"],
            inner_comment_markers: &[],
            name_fields: &[],
        },
        _ => return None,
    };
    Some(language_support)
}
