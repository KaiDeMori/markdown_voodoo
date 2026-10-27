#![allow(non_camel_case_types)]

mod languages;
mod outline;
mod read;
mod toc;

use std::path::Path;
use std::process::ExitCode;

use outline::Outline;

const TOC_USAGE: &str = "usage: calm-code toc [--page <number>] <file> [name ... | @number]";
const READ_USAGE: &str = "usage: calm-code read [--limit <characters>] <file> <name ... | @number>";
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
    let Some((file, name_path)) = arguments.split_first() else {
        return Err(TOC_USAGE.to_string());
    };
    let (outline, _) = load_outline(file)?;
    toc::render(&outline, name_path, page.unwrap_or(1)).map_err(|refusal| format!("{file}: {refusal}"))
}

fn run_read(arguments: &[String]) -> Result<String, String> {
    let (limit, arguments) = take_number_option(arguments, "--limit")?;
    let Some((file, name_path)) = arguments.split_first().filter(|(_, name_path)| !name_path.is_empty()) else {
        return Err(READ_USAGE.to_string());
    };
    let (outline, source) = load_outline(file)?;
    if outline.syntax_error_count > 0 {
        eprintln!(
            "{}, the lines may be incomplete",
            toc::counted(outline.syntax_error_count, "syntax error")
        );
    }
    read::render(&outline, &source, file, name_path, limit.unwrap_or(DEFAULT_READ_LIMIT))
        .map_err(|refusal| format!("{file}: {refusal}"))
}

/// The option may stand anywhere after the command, since no name starts with two dashes.
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

fn load_outline(file: &str) -> Result<(Outline, String), String> {
    let path = Path::new(file);
    if path.is_dir() {
        return Err(format!("{file}: a folder, not a file"));
    }
    if !path.is_file() {
        return Err(format!("{file}: no such file"));
    }
    let language_support = languages::language_for(path).ok_or_else(|| match path.extension() {
        Some(extension) => format!("{file}: no grammar for .{} files", extension.to_string_lossy()),
        None => format!("{file}: no grammar for files without an extension"),
    })?;
    let bytes = std::fs::read(path).map_err(|error| format!("{file}: {error}"))?;
    let text = String::from_utf8(bytes).map_err(|_| format!("{file}: not UTF-8 text"))?;
    let source = match text.strip_prefix('\u{feff}') {
        Some(without_byte_order_mark) => without_byte_order_mark.to_string(),
        None => text,
    };
    let outline =
        outline::build_outline(&source, &language_support).map_err(|problem| format!("{file}: {problem}"))?;
    Ok((outline, source))
}
