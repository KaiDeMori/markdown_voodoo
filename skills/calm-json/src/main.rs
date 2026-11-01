#![allow(non_camel_case_types)]

mod document;
mod json_path;
mod read;
mod toc;

use std::path::Path;
use std::process::ExitCode;

use document::Document;

const TOC_USAGE: &str = "usage: calm-json toc [--page <number>] <file> [path | @number]";
const READ_USAGE: &str = "usage: calm-json read [--limit <characters>] <file> <path | @number>";
const DEFAULT_READ_LIMIT: usize = 20_000;

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    match run(&arguments) {
        Ok(output) => {
            print!("{output}");
            ExitCode::SUCCESS
        }
        Err(refusal) => {
            eprintln!("{refusal}");
            ExitCode::FAILURE
        }
    }
}

fn run(arguments: &[String]) -> Result<String, String> {
    match arguments.split_first() {
        Some((command, rest)) if command == "toc" => run_toc(rest),
        Some((command, rest)) if command == "read" => run_read(rest),
        _ => Err(format!("{TOC_USAGE}\n{READ_USAGE}")),
    }
}

fn run_toc(arguments: &[String]) -> Result<String, String> {
    let (page, arguments) = take_number_option(arguments, "--page")?;
    let (file, path) = match arguments.as_slice() {
        [file] => (file, None),
        [file, path] => (file, Some(path.as_str())),
        _ => return Err(TOC_USAGE.to_string()),
    };
    let (document, source) = load_document(file)?;
    toc::render(&document, &source, path, page.unwrap_or(1)).map_err(|refusal| format!("{file}: {refusal}"))
}

fn run_read(arguments: &[String]) -> Result<String, String> {
    let (limit, arguments) = take_number_option(arguments, "--limit")?;
    let [file, path] = arguments.as_slice() else {
        return Err(READ_USAGE.to_string());
    };
    let (document, source) = load_document(file)?;
    if document.syntax_error_count > 0 {
        eprintln!(
            "{}, the text may be incomplete",
            toc::counted(document.syntax_error_count, "syntax error")
        );
    }
    read::render(&document, &source, file, path, limit.unwrap_or(DEFAULT_READ_LIMIT))
        .map_err(|refusal| format!("{file}: {refusal}"))
}

/// The option may stand anywhere after the command; a key that starts with two dashes goes in brackets and quotes.
fn take_number_option(arguments: &[String], option_name: &str) -> Result<(Option<usize>, Vec<String>), String> {
    let mut number = None;
    let mut rest = Vec::new();
    let mut remaining = arguments.iter();
    while let Some(argument) = remaining.next() {
        if argument == option_name {
            let value = remaining.next().ok_or_else(|| format!("{option_name} needs a number"))?;
            let parsed = value
                .parse::<usize>()
                .ok()
                .filter(|&parsed| parsed >= 1)
                .ok_or_else(|| format!("{option_name} needs a number from 1 on, not {value}"))?;
            number = Some(parsed);
        } else if argument.starts_with("--") {
            return Err(format!("unknown option {argument}"));
        } else {
            rest.push(argument.clone());
        }
    }
    Ok((number, rest))
}

fn load_document(file: &str) -> Result<(Document, String), String> {
    let path = Path::new(file);
    if path.is_dir() {
        return Err(format!("{file}: a folder, not a file"));
    }
    if !path.is_file() {
        return Err(format!("{file}: no such file"));
    }
    let bytes = std::fs::read(path).map_err(|error| format!("{file}: {error}"))?;
    let text = String::from_utf8(bytes).map_err(|_| format!("{file}: not UTF-8 text"))?;
    let source = match text.strip_prefix('\u{feff}') {
        Some(without_byte_order_mark) => without_byte_order_mark.to_string(),
        None => text,
    };
    let document = document::build_document(&source).map_err(|problem| format!("{file}: {problem}"))?;
    Ok((document, source))
}
