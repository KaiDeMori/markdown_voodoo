#![allow(non_camel_case_types)]

mod languages;
mod outline;
mod toc;

use std::path::Path;
use std::process::ExitCode;

use outline::Outline;

const USAGE: &str = "usage: toc [--page <number>] <file> [name ... | @number]";

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
        _ => Err(USAGE.to_string()),
    }
}

fn run_toc(arguments: &[String]) -> Result<String, String> {
    let (page, arguments) = take_page_option(arguments)?;
    let Some((file, name_path)) = arguments.split_first() else {
        return Err(USAGE.to_string());
    };
    let outline = load_outline(file)?;
    toc::render(&outline, name_path, page).map_err(|refusal| format!("{file}: {refusal}"))
}

fn take_page_option(arguments: &[String]) -> Result<(usize, &[String]), String> {
    match arguments {
        [option, value, rest @ ..] if option == "--page" => {
            let page = value
                .parse::<usize>()
                .ok()
                .filter(|&page| page >= 1)
                .ok_or_else(|| format!("--page needs a number from 1 on, not {value}"))?;
            Ok((page, rest))
        }
        [option] if option == "--page" => Err("--page needs a number".to_string()),
        [option, ..] if option.starts_with("--") => Err(format!("unknown option {option}")),
        _ => Ok((1, arguments)),
    }
}

fn load_outline(file: &str) -> Result<Outline, String> {
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
    let source = text.strip_prefix('\u{feff}').unwrap_or(&text);
    outline::build_outline(source, &language_support).map_err(|problem| format!("{file}: {problem}"))
}
