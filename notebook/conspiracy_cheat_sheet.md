# Conspiracy cheat sheet

## The real trick

What is the right question, and what are the right thresholds?

- A raven is only as good as its question; when a raven comes back wrong, the question was wrong.
- The thresholds of `haven:/Hall/thresholds.md` tell it where to pause: not yet, not all at once, not mine.
- A bump is a threshold too: a raven usually reports it back briefly instead of fixing it, and we decide together.

## Single-agent workflow

Scope: one agent through `Workflow`, with `model` and `effort` set explicitly.
This sheet replaces the `workflow-authoring` skill for that case.
If something here fails, ask Wally, or send a raven to look it up in that skill; the skill itself stays out of this window.
Source: that skill, 2026-10-18.

### House rule

- Single agents go through `Workflow` too.
- Always set both `model` and `effort`. The skill says to omit them. This rule overrides that.
- `effort` is the reasoning setting, and it is always `'max'`.

### Script

```js
export const meta = {
  name: 'single_agent_run',
  description: 'One agent with explicit model and effort',
}
const answer = await agent('PROMPT_TEXT', {
  model: 'sonnet',
  effort: 'max',
})
return answer
```

- Pass it inline as the `script` input. Do not write it to a file first. Do not set `name` with it.
- `meta` comes first and carries name and description. The tool's own `title` and `description` inputs are ignored.
- The call returns at once. The result arrives later as a `<task-notification>`. Nothing to poll.
- To iterate: the tool result names the saved script file. Edit it, then call `Workflow` with `scriptPath`.

### Options of `agent(prompt, opts)`

- `model`: string. The skill lists no valid values and this is not verified for `agent()`. Try the aliases of the Agent tool's `model` enum (`sonnet`, `opus`, `haiku`, `fable` on 2026-10-18).
- `effort`: `'max'`.
- `schema`: JSON Schema. The agent then returns a validated object instead of text. Example: `{type: 'object', properties: {summary: {type: 'string'}}, required: ['summary']}`. The root must be an object. `required` must be a subset of `properties`.
- `label`: name in the progress display.
- `agentType`: custom subagent type instead of the default, e.g. `'general-purpose'`.
- Not needed for one agent: `phase`, `isolation`.

Return value: the final text, or the object when `schema` is set.
It is `null` if the user skips the agent or it dies on a terminal API error. Check before use.

### Prompt

- The agent is already told that its final text is the return value. Do not repeat that.
- The return value is what comes back to you. Keep it small: ask for a compact result or use `schema`.
- The agent already gets the same CLAUDE.md files, except built-in types such as Explore and Plan. Do not paste or re-read them.
- For variable input, pass `args` to `Workflow` and read `args` in the script. Give objects and arrays as real JSON, not as a JSON string.

### Gotchas

- Plain JavaScript. No TypeScript syntax.
- `meta` is a pure literal: no variables, calls, spreads or template strings.
- `Date.now()`, `Math.random()` and argless `new Date()` throw.
- No filesystem or Node APIs in the script.

### Ignore for one agent

`parallel`, `pipeline`, `phase`, `log`, `budget`, `workflow()`, `resumeFromRunId`, the quality patterns and ultracode.
