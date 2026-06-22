# Q and A Tool Usage Guide

This document explains the general concept of using the VS Code `askQuestions` API as a question-and-answer interaction tool.

## Purpose

Use the tool to orchestrate a short interactive dialog that collects user input step-by-step. Each question can be adapted depending on previous answers, enabling dynamic conversational flows.

## Pattern

1. Send the first question request through `vscode_askQuestions`.
2. Receive the user response.
3. Decide on the next question content based on the response.
4. Send the next question request.
5. Continue until the required information is collected.

## Best practices

- Keep the flow simple and deterministic.
- Use previous responses to inform follow-up questions.
- Validate if required fields are provided, and re-prompt as needed.
