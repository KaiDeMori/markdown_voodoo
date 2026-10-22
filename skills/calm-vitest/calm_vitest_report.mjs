// calm_vitest_report: reads a Vitest JSON report and tells how the run went, in as few lines as the question needs.
// A sentence is the first line of a failure's message; failures that say the same sentence count once.
// Usage: node calm_vitest_report.mjs <report> overview <line_limit>
//        node calm_vitest_report.mjs <report> where <file>
//        node calm_vitest_report.mjs <report> what <file> <test name>

import { readFileSync } from "node:fs";
import { isAbsolute, relative } from "node:path";

// A sentence is cut to this many characters; where shows at most this many blocks, and this many sentences per block.
const sentence_characters = 120;
const block_limit = 20;
const sentences_per_block = 10;
const test_file_ending = /\.(test|spec)\.[cm]?[jt]sx?$/;

const [report_location, mode, ...words] = process.argv.slice(2);
const report = JSON.parse(readFileSync(report_location, "utf8"));

function fail(line) {
  console.log(line);
  process.exit(1);
}

function count(number, word) {
  return `${number} ${word}${number === 1 ? "" : "s"}`;
}

// Colors would only be noise in a window.
function plain(text) {
  return (text ?? "").replace(/\u001b\[[0-9;]*m/g, "");
}

function cut(text) {
  return text.length > sentence_characters ? `${text.slice(0, sentence_characters)}...` : text;
}

function first_line(text) {
  return (plain(text).split("\n").find((line) => line.trim()) ?? "(no message)").trim();
}

function label_of(path) {
  // The path from the workspace, without its .test.ts ending: tests/memory/data_and_storage names one file.
  const from_workspace = isAbsolute(path) ? relative(process.cwd(), path) : path;
  return from_workspace.replaceAll("\\", "/").replace(test_file_ending, "");
}

function block_of(test) {
  return test.ancestorTitles.length ? test.ancestorTitles.join(" > ") : "(top level)";
}

function failed_tests(file) {
  return file.assertionResults.filter((test) => test.status === "failed");
}

function sentence_of(test) {
  return first_line(test.failureMessages?.[0]);
}

function file_line(file) {
  const label = label_of(file.name);
  if (file.status !== "failed") {
    return `${label}: green`;
  }
  const failed = failed_tests(file);
  // A file that could not even load has no tests, only its message.
  if (!failed.length) {
    return `${label}: did not run, 1 sentence`;
  }
  const blocks = new Set(failed.map(block_of));
  const sentences = new Set(failed.map(sentence_of));
  return `${label}: ${count(blocks.size, "block")} red, ${count(failed.length, "test")}, ${count(sentences.size, "sentence")}`;
}

function show_overview(line_limit) {
  const files = report.testResults;
  if (!files.length) {
    console.log("no test files");
    return;
  }
  // Red first: it is what a raven came for.
  const red = files.filter((file) => file.status === "failed");
  const ordered = [...red, ...files.filter((file) => file.status !== "failed")];
  for (const file of ordered.slice(0, line_limit)) {
    console.log(file_line(file));
  }
  const rest = ordered.slice(line_limit);
  if (rest.length) {
    const red_rest = rest.filter((file) => file.status === "failed").length;
    console.log(`and ${rest.length} more, ${red_rest ? `${red_rest} of them red` : "all green"}`);
  }
}

function find_file(wanted) {
  // A file is named by its path or its label, or by the end of it, as long as only one file fits.
  const wanted_label = label_of(wanted);
  const fits = report.testResults.filter((file) => {
    const label = label_of(file.name);
    return label === wanted_label || label.endsWith(`/${wanted_label}`);
  });
  if (fits.length === 1) {
    return fits[0];
  }
  if (!fits.length) {
    fail(`${wanted} is not in the last run.`);
  }
  fail(`${wanted} fits ${fits.length} files: ${fits.map((file) => label_of(file.name)).join(", ")}`);
}

function show_where(wanted) {
  if (!wanted) {
    fail("where <file>?");
  }
  const file = find_file(wanted);
  if (file.status !== "failed") {
    console.log(`${label_of(file.name)}: green`);
    return;
  }
  const failed = failed_tests(file);
  if (!failed.length) {
    console.log(`did not run: ${cut(first_line(file.message))}`);
    return;
  }
  const blocks = new Map();
  for (const test of failed) {
    const block = block_of(test);
    if (!blocks.has(block)) {
      blocks.set(block, new Map());
    }
    const sentences = blocks.get(block);
    const sentence = sentence_of(test);
    sentences.set(sentence, (sentences.get(sentence) ?? 0) + 1);
  }
  const shown_blocks = [...blocks].slice(0, block_limit);
  for (const [block, sentences] of shown_blocks) {
    const tests = [...sentences.values()].reduce((sum, times) => sum + times, 0);
    console.log(`${block}: ${count(tests, "test")}, ${count(sentences.size, "sentence")}`);
    const shown_sentences = [...sentences].slice(0, sentences_per_block);
    for (const [sentence, times] of shown_sentences) {
      console.log(`  ${times}  ${cut(sentence)}`);
    }
    if (sentences.size > shown_sentences.length) {
      console.log(`  and ${sentences.size - shown_sentences.length} more sentences`);
    }
  }
  if (blocks.size > shown_blocks.length) {
    console.log(`and ${blocks.size - shown_blocks.length} more red blocks`);
  }
}

function show_what(wanted_file, wanted_test) {
  if (!wanted_file || !wanted_test) {
    fail("what <file> <test name>?");
  }
  const file = find_file(wanted_file);
  if (file.status === "failed" && !file.assertionResults.length) {
    console.log(plain(file.message));
    return;
  }
  // A test is named by its title, or by its block and title, as where shows them.
  const fits = file.assertionResults.filter((test) => test.title === wanted_test || `${block_of(test)} > ${test.title}` === wanted_test);
  if (!fits.length) {
    fail(`${wanted_test} is not in ${label_of(file.name)}.`);
  }
  if (fits.length > 1) {
    fail(`${wanted_test} fits ${fits.length} tests; name it with its block: ${fits.map((test) => `${block_of(test)} > ${test.title}`).join(", ")}`);
  }
  const test = fits[0];
  console.log(`${block_of(test)} > ${test.title}: ${test.status}`);
  for (const message of test.failureMessages ?? []) {
    console.log(plain(message));
  }
}

if (mode === "overview") {
  show_overview(Number(words[0]) || 20);
} else if (mode === "where") {
  show_where(words[0]);
} else if (mode === "what") {
  show_what(words[0], words.slice(1).join(" "));
} else {
  fail("overview, where or what?");
}
