use std::path::Path;

use tree_sitter::Language;

pub struct Language_support {
    pub name: &'static str,
    pub grammar: Language,
    pub definitions_query: &'static str,
    /// Nodes of these kinds wrap a definition and belong to it, so decorators and export keywords travel with it.
    pub wrapper_kinds: &'static [&'static str],
}

pub fn language_for(path: &Path) -> Option<Language_support> {
    let extension = path.extension()?.to_str()?.to_ascii_lowercase();
    let language_support = match extension.as_str() {
        "cs" => Language_support {
            name: "C#",
            grammar: tree_sitter_c_sharp::LANGUAGE.into(),
            definitions_query: include_str!("queries/c_sharp.scm"),
            wrapper_kinds: &[],
        },
        "py" | "pyw" => Language_support {
            name: "Python",
            grammar: tree_sitter_python::LANGUAGE.into(),
            definitions_query: include_str!("queries/python.scm"),
            wrapper_kinds: &["decorated_definition"],
        },
        "js" | "mjs" | "cjs" | "jsx" => Language_support {
            name: "JavaScript",
            grammar: tree_sitter_javascript::LANGUAGE.into(),
            definitions_query: include_str!("queries/javascript.scm"),
            wrapper_kinds: &["export_statement", "lexical_declaration", "variable_declaration"],
        },
        _ => return None,
    };
    Some(language_support)
}
