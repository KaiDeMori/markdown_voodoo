Title: Agent Skills Overview - Agent Skills

URL Source: https://agentskills.io/

Published Time: Mon, 27 Jul 2026 18:35:14 GMT

Markdown Content:
A standardized way to give AI agents new capabilities and expertise.

## What are Agent Skills?

Agent Skills are a lightweight, open format for extending AI agent capabilities with specialized knowledge and workflows.At its core, a skill is a folder containing a `SKILL.md` file. This file includes metadata (`name` and `description`, at minimum) and instructions that tell an agent how to perform a specific task. Skills can also bundle scripts, reference materials, templates, and other resources.

## Why Agent Skills?

Agents are increasingly capable, but often don’t have the context they need to do real work reliably. Skills solve this by packaging procedural knowledge and company-, team-, and user-specific context into portable, version-controlled folders that agents load on demand. This gives agents:

*   **Domain expertise**: Capture specialized knowledge — from legal review processes to data analysis pipelines to presentation formatting — as reusable instructions and resources.
*   **Repeatable workflows**: Turn multi-step tasks into consistent, auditable procedures.
*   **Cross-product reuse**: Build a skill once and use it across any skills-compatible agent.

## How do Agent Skills work?

Agents load skills through **progressive disclosure**, in three stages:

1.   **Discovery**: At startup, agents load only the name and description of each available skill, just enough to know when it might be relevant.
2.   **Activation**: When a task matches a skill’s description, the agent reads the full `SKILL.md` instructions into context.
3.   **Execution**: The agent follows the instructions, optionally executing bundled code or loading referenced files as needed.

Full instructions load only when a task calls for them, so agents can keep many skills on hand with only a small context footprint.

## Where can I use Agent Skills?

Agent Skills are supported by a large number of AI tools and agentic clients — see the [Client Showcase](https://agentskills.io/clients) to explore some of them!

[![Image 1: Cursor](https://agentskills.io/images/logos/cursor/LOCKUP_HORIZONTAL_2D_LIGHT.svg)![Image 2: Cursor](https://agentskills.io/images/logos/cursor/LOCKUP_HORIZONTAL_2D_DARK.svg)](https://cursor.com/)

[![Image 3: bub](https://agentskills.io/images/logos/bub/bub-light.svg)![Image 4: bub](https://agentskills.io/images/logos/bub/bub-dark.svg)](https://bub.build/)

[![Image 5: Roo Code](https://agentskills.io/images/logos/roo-code/roo-code-logo-black.svg)![Image 6: Roo Code](https://agentskills.io/images/logos/roo-code/roo-code-logo-white.svg)](https://roocode.com/)

[![Image 7: fast-agent](https://agentskills.io/images/logos/fast-agent/fast-agent-light.svg)![Image 8: fast-agent](https://agentskills.io/images/logos/fast-agent/fast-agent-dark.svg)](https://fast-agent.ai/)

[![Image 9: nanobot](https://agentskills.io/images/logos/nanobot/nanobot-logo-light.png)![Image 10: nanobot](https://agentskills.io/images/logos/nanobot/nanobot-logo-dark.png)](https://nanobot.wiki/)

[![Image 11: ZeroClaw](https://agentskills.io/images/logos/zeroclaw/zeroclaw-logo-light.png)![Image 12: ZeroClaw](https://agentskills.io/images/logos/zeroclaw/zeroclaw-logo-dark.png)](https://www.zeroclawlabs.ai/)

[![Image 13: Claude](https://agentskills.io/images/logos/claude-ai/Claude-logo-Slate.svg)![Image 14: Claude](https://agentskills.io/images/logos/claude-ai/Claude-logo-Ivory.svg)](https://claude.ai/)

[![Image 15: Gemini CLI](https://agentskills.io/images/logos/gemini-cli/gemini-cli-logo_light.svg)![Image 16: Gemini CLI](https://agentskills.io/images/logos/gemini-cli/gemini-cli-logo_dark.svg)](https://geminicli.com/)

[![Image 17: Superconductor](https://agentskills.io/images/logos/superconductor/superconductor-wordmark-light.svg)![Image 18: Superconductor](https://agentskills.io/images/logos/superconductor/superconductor-wordmark-dark.svg)](https://superconductor.com/)

[![Image 19: Piebald](https://agentskills.io/images/logos/piebald/Piebald_wordmark_light.svg)![Image 20: Piebald](https://agentskills.io/images/logos/piebald/Piebald_wordmark_dark.svg)](https://piebald.ai/)

[![Image 21: Snowflake Cortex Code](https://agentskills.io/images/logos/snowflake/snowflake-logo-light.svg)![Image 22: Snowflake Cortex Code](https://agentskills.io/images/logos/snowflake/snowflake-logo-dark.svg)](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code)

[![Image 23: Letta](https://agentskills.io/images/logos/letta/Letta-logo-RGB_OffBlackonTransparent.svg)![Image 24: Letta](https://agentskills.io/images/logos/letta/Letta-logo-RGB_GreyonTransparent.svg)](https://www.letta.com/)

[![Image 25: Vita](https://agentskills.io/images/logos/vita/logo-horizontal-light.svg)![Image 26: Vita](https://agentskills.io/images/logos/vita/logo-horizontal-dark.svg)](https://www.vita-ai.net/)

[![Image 27: Mistral AI Vibe](https://agentskills.io/images/logos/mistral-vibe/vibe-logo_black.svg)![Image 28: Mistral AI Vibe](https://agentskills.io/images/logos/mistral-vibe/vibe-logo_white.svg)](https://github.com/mistralai/mistral-vibe)

[![Image 29: Emdash](https://agentskills.io/images/logos/emdash/emdash-logo-light.svg)![Image 30: Emdash](https://agentskills.io/images/logos/emdash/emdash-logo-dark.svg)](https://emdash.sh/)

[![Image 31: pi](https://agentskills.io/images/logos/pi/pi-logo-light.svg)![Image 32: pi](https://agentskills.io/images/logos/pi/pi-logo-dark.svg)](https://shittycodingagent.ai/)

[![Image 33: Junie](https://agentskills.io/images/logos/junie/junie-logo-on-white.svg)![Image 34: Junie](https://agentskills.io/images/logos/junie/junie-logo-on-dark.svg)](https://junie.jetbrains.com/)

[![Image 35: Workshop](https://agentskills.io/images/logos/workshop/workshop-logo-light.svg)![Image 36: Workshop](https://agentskills.io/images/logos/workshop/workshop-logo-dark.svg)](https://workshop.ai/)

[![Image 37: Qodo](https://agentskills.io/images/logos/qodo/qodo-logo-light.png)![Image 38: Qodo](https://agentskills.io/images/logos/qodo/qodo-logo-dark.svg)](https://www.qodo.ai/)

[![Image 39: Spring AI](https://agentskills.io/images/logos/spring-ai/spring-ai-logo-light.svg)![Image 40: Spring AI](https://agentskills.io/images/logos/spring-ai/spring-ai-logo-dark.svg)](https://docs.spring.io/spring-ai/reference)

[![Image 41: Deep Code](https://agentskills.io/images/logos/deepcode/deepcode-logo-light.svg)![Image 42: Deep Code](https://agentskills.io/images/logos/deepcode/deepcode-logo-dark.svg)](https://deepcode.vegamo.cn/en)

[![Image 43: Kiro](https://agentskills.io/images/logos/kiro/kiro-logo-light.svg)![Image 44: Kiro](https://agentskills.io/images/logos/kiro/kiro-logo-dark.svg)](https://kiro.dev/)

[![Image 45: GitHub Copilot](https://agentskills.io/images/logos/github/GitHub_Lockup_Dark.svg)![Image 46: GitHub Copilot](https://agentskills.io/images/logos/github/GitHub_Lockup_Light.svg)](https://github.com/)

[![Image 47: Agentman](https://agentskills.io/images/logos/agentman/agentman-wordmark-light.svg)![Image 48: Agentman](https://agentskills.io/images/logos/agentman/agentman-wordmark-dark.svg)](https://agentman.ai/)

[![Image 49: Tabnine](https://agentskills.io/images/logos/tabnine/tabnine-logo-light.svg)![Image 50: Tabnine](https://agentskills.io/images/logos/tabnine/tabnine-logo-dark.svg)](https://www.tabnine.com/)

[![Image 51: Factory](https://agentskills.io/images/logos/factory/factory-logo-light.svg)![Image 52: Factory](https://agentskills.io/images/logos/factory/factory-logo-dark.svg)](https://factory.ai/)

[![Image 53: Autohand Code CLI](https://agentskills.io/images/logos/autohand/autohand-light.svg)![Image 54: Autohand Code CLI](https://agentskills.io/images/logos/autohand/autohand-dark.svg)](https://autohand.ai/)

[![Image 55: Databricks Genie Code](https://agentskills.io/images/logos/databricks/databricks-logo-light.svg)![Image 56: Databricks Genie Code](https://agentskills.io/images/logos/databricks/databricks-logo-dark.svg)](https://databricks.com/)

[![Image 57: Goose](https://agentskills.io/images/logos/goose/goose-logo-black.png)![Image 58: Goose](https://agentskills.io/images/logos/goose/goose-logo-white.png)](https://block.github.io/goose/)

[![Image 59: Firebender](https://agentskills.io/images/logos/firebender/firebender-wordmark-light.svg)![Image 60: Firebender](https://agentskills.io/images/logos/firebender/firebender-wordmark-dark.svg)](https://firebender.com/)

[![Image 61: OpenAI Codex](https://agentskills.io/images/logos/oai-codex/OAI_Codex-Lockup_400px.svg)![Image 62: OpenAI Codex](https://agentskills.io/images/logos/oai-codex/OAI_Codex-Lockup_400px_Darkmode.svg)](https://developers.openai.com/codex)

[![Image 63: VT Code](https://agentskills.io/images/logos/vtcode/vt_code_light.svg)![Image 64: VT Code](https://agentskills.io/images/logos/vtcode/vt_code_dark.svg)](https://github.com/vinhnx/vtcode)

[![Image 65: Google AI Edge Gallery](https://agentskills.io/images/logos/google-ai-edge-gallery/google-ai-edge-gallery-light.svg)![Image 66: Google AI Edge Gallery](https://agentskills.io/images/logos/google-ai-edge-gallery/google-ai-edge-gallery-dark.svg)](https://github.com/google-ai-edge/gallery)

[![Image 67: Amp](https://agentskills.io/images/logos/amp/amp-logo-light.svg)![Image 68: Amp](https://agentskills.io/images/logos/amp/amp-logo-dark.svg)](https://ampcode.com/)

[![Image 69: Laravel Boost](https://agentskills.io/images/logos/laravel-boost/boost-light-mode.svg)![Image 70: Laravel Boost](https://agentskills.io/images/logos/laravel-boost/boost-dark-mode.svg)](https://github.com/laravel/boost)

[![Image 71: TRAE](https://agentskills.io/images/logos/trae/trae-logo-lightmode.svg)![Image 72: TRAE](https://agentskills.io/images/logos/trae/trae-logo-darkmode.svg)](https://trae.ai/)

[![Image 73: Pulumi Neo](https://agentskills.io/images/logos/pulumi-neo/pulumi-neo-logo-light.svg)![Image 74: Pulumi Neo](https://agentskills.io/images/logos/pulumi-neo/pulumi-neo-logo-dark.svg)](https://www.pulumi.com/product/neo/)

[![Image 75: VS Code](https://agentskills.io/images/logos/vscode/vscode.svg)![Image 76: VS Code](https://agentskills.io/images/logos/vscode/vscode-alt.svg)](https://code.visualstudio.com/)

[![Image 77: Claude Code](https://agentskills.io/images/logos/claude-code/Claude-Code-logo-Slate.svg)![Image 78: Claude Code](https://agentskills.io/images/logos/claude-code/Claude-Code-logo-Ivory.svg)](https://claude.ai/code)

[![Image 79: OpenCode](https://agentskills.io/images/logos/opencode/opencode-wordmark-light.svg)![Image 80: OpenCode](https://agentskills.io/images/logos/opencode/opencode-wordmark-dark.svg)](https://opencode.ai/)

[![Image 81: Command Code](https://agentskills.io/images/logos/command-code/command-code-logo-for-light.svg)![Image 82: Command Code](https://agentskills.io/images/logos/command-code/command-code-logo-for-dark.svg)](https://commandcode.ai/)

[![Image 83: OpenHands](https://agentskills.io/images/logos/openhands/openhands-logo-light.svg)![Image 84: OpenHands](https://agentskills.io/images/logos/openhands/openhands-logo-dark.svg)](https://openhands.dev/)

[![Image 85: Ona](https://agentskills.io/images/logos/ona/ona-wordmark-light.svg)![Image 86: Ona](https://agentskills.io/images/logos/ona/ona-wordmark-dark.svg)](https://ona.com/)

[![Image 87: Mux](https://agentskills.io/images/logos/mux/mux-editor-light.svg)![Image 88: Mux](https://agentskills.io/images/logos/mux/mux-editor-dark.svg)](https://mux.coder.com/)

[![Image 89: Cursor](https://agentskills.io/images/logos/cursor/LOCKUP_HORIZONTAL_2D_LIGHT.svg)![Image 90: Cursor](https://agentskills.io/images/logos/cursor/LOCKUP_HORIZONTAL_2D_DARK.svg)](https://cursor.com/)

[![Image 91: bub](https://agentskills.io/images/logos/bub/bub-light.svg)![Image 92: bub](https://agentskills.io/images/logos/bub/bub-dark.svg)](https://bub.build/)

[![Image 93: Roo Code](https://agentskills.io/images/logos/roo-code/roo-code-logo-black.svg)![Image 94: Roo Code](https://agentskills.io/images/logos/roo-code/roo-code-logo-white.svg)](https://roocode.com/)

[![Image 95: fast-agent](https://agentskills.io/images/logos/fast-agent/fast-agent-light.svg)![Image 96: fast-agent](https://agentskills.io/images/logos/fast-agent/fast-agent-dark.svg)](https://fast-agent.ai/)

[![Image 97: nanobot](https://agentskills.io/images/logos/nanobot/nanobot-logo-light.png)![Image 98: nanobot](https://agentskills.io/images/logos/nanobot/nanobot-logo-dark.png)](https://nanobot.wiki/)

[![Image 99: ZeroClaw](https://agentskills.io/images/logos/zeroclaw/zeroclaw-logo-light.png)![Image 100: ZeroClaw](https://agentskills.io/images/logos/zeroclaw/zeroclaw-logo-dark.png)](https://www.zeroclawlabs.ai/)

[![Image 101: Claude](https://agentskills.io/images/logos/claude-ai/Claude-logo-Slate.svg)![Image 102: Claude](https://agentskills.io/images/logos/claude-ai/Claude-logo-Ivory.svg)](https://claude.ai/)

[![Image 103: Gemini CLI](https://agentskills.io/images/logos/gemini-cli/gemini-cli-logo_light.svg)![Image 104: Gemini CLI](https://agentskills.io/images/logos/gemini-cli/gemini-cli-logo_dark.svg)](https://geminicli.com/)

[![Image 105: Superconductor](https://agentskills.io/images/logos/superconductor/superconductor-wordmark-light.svg)![Image 106: Superconductor](https://agentskills.io/images/logos/superconductor/superconductor-wordmark-dark.svg)](https://superconductor.com/)

[![Image 107: Piebald](https://agentskills.io/images/logos/piebald/Piebald_wordmark_light.svg)![Image 108: Piebald](https://agentskills.io/images/logos/piebald/Piebald_wordmark_dark.svg)](https://piebald.ai/)

[![Image 109: Snowflake Cortex Code](https://agentskills.io/images/logos/snowflake/snowflake-logo-light.svg)![Image 110: Snowflake Cortex Code](https://agentskills.io/images/logos/snowflake/snowflake-logo-dark.svg)](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code)

[![Image 111: Letta](https://agentskills.io/images/logos/letta/Letta-logo-RGB_OffBlackonTransparent.svg)![Image 112: Letta](https://agentskills.io/images/logos/letta/Letta-logo-RGB_GreyonTransparent.svg)](https://www.letta.com/)

[![Image 113: Vita](https://agentskills.io/images/logos/vita/logo-horizontal-light.svg)![Image 114: Vita](https://agentskills.io/images/logos/vita/logo-horizontal-dark.svg)](https://www.vita-ai.net/)

[![Image 115: Mistral AI Vibe](https://agentskills.io/images/logos/mistral-vibe/vibe-logo_black.svg)![Image 116: Mistral AI Vibe](https://agentskills.io/images/logos/mistral-vibe/vibe-logo_white.svg)](https://github.com/mistralai/mistral-vibe)

[![Image 117: Emdash](https://agentskills.io/images/logos/emdash/emdash-logo-light.svg)![Image 118: Emdash](https://agentskills.io/images/logos/emdash/emdash-logo-dark.svg)](https://emdash.sh/)

[![Image 119: pi](https://agentskills.io/images/logos/pi/pi-logo-light.svg)![Image 120: pi](https://agentskills.io/images/logos/pi/pi-logo-dark.svg)](https://shittycodingagent.ai/)

[![Image 121: Junie](https://agentskills.io/images/logos/junie/junie-logo-on-white.svg)![Image 122: Junie](https://agentskills.io/images/logos/junie/junie-logo-on-dark.svg)](https://junie.jetbrains.com/)

[![Image 123: Workshop](https://agentskills.io/images/logos/workshop/workshop-logo-light.svg)![Image 124: Workshop](https://agentskills.io/images/logos/workshop/workshop-logo-dark.svg)](https://workshop.ai/)

[![Image 125: Qodo](https://agentskills.io/images/logos/qodo/qodo-logo-light.png)![Image 126: Qodo](https://agentskills.io/images/logos/qodo/qodo-logo-dark.svg)](https://www.qodo.ai/)

[![Image 127: Spring AI](https://agentskills.io/images/logos/spring-ai/spring-ai-logo-light.svg)![Image 128: Spring AI](https://agentskills.io/images/logos/spring-ai/spring-ai-logo-dark.svg)](https://docs.spring.io/spring-ai/reference)

[![Image 129: Deep Code](https://agentskills.io/images/logos/deepcode/deepcode-logo-light.svg)![Image 130: Deep Code](https://agentskills.io/images/logos/deepcode/deepcode-logo-dark.svg)](https://deepcode.vegamo.cn/en)

[![Image 131: Kiro](https://agentskills.io/images/logos/kiro/kiro-logo-light.svg)![Image 132: Kiro](https://agentskills.io/images/logos/kiro/kiro-logo-dark.svg)](https://kiro.dev/)

[![Image 133: GitHub Copilot](https://agentskills.io/images/logos/github/GitHub_Lockup_Dark.svg)![Image 134: GitHub Copilot](https://agentskills.io/images/logos/github/GitHub_Lockup_Light.svg)](https://github.com/)

[![Image 135: Agentman](https://agentskills.io/images/logos/agentman/agentman-wordmark-light.svg)![Image 136: Agentman](https://agentskills.io/images/logos/agentman/agentman-wordmark-dark.svg)](https://agentman.ai/)

[![Image 137: Tabnine](https://agentskills.io/images/logos/tabnine/tabnine-logo-light.svg)![Image 138: Tabnine](https://agentskills.io/images/logos/tabnine/tabnine-logo-dark.svg)](https://www.tabnine.com/)

[![Image 139: Factory](https://agentskills.io/images/logos/factory/factory-logo-light.svg)![Image 140: Factory](https://agentskills.io/images/logos/factory/factory-logo-dark.svg)](https://factory.ai/)

[![Image 141: Autohand Code CLI](https://agentskills.io/images/logos/autohand/autohand-light.svg)![Image 142: Autohand Code CLI](https://agentskills.io/images/logos/autohand/autohand-dark.svg)](https://autohand.ai/)

[![Image 143: Databricks Genie Code](https://agentskills.io/images/logos/databricks/databricks-logo-light.svg)![Image 144: Databricks Genie Code](https://agentskills.io/images/logos/databricks/databricks-logo-dark.svg)](https://databricks.com/)

[![Image 145: Goose](https://agentskills.io/images/logos/goose/goose-logo-black.png)![Image 146: Goose](https://agentskills.io/images/logos/goose/goose-logo-white.png)](https://block.github.io/goose/)

[![Image 147: Firebender](https://agentskills.io/images/logos/firebender/firebender-wordmark-light.svg)![Image 148: Firebender](https://agentskills.io/images/logos/firebender/firebender-wordmark-dark.svg)](https://firebender.com/)

[![Image 149: OpenAI Codex](https://agentskills.io/images/logos/oai-codex/OAI_Codex-Lockup_400px.svg)![Image 150: OpenAI Codex](https://agentskills.io/images/logos/oai-codex/OAI_Codex-Lockup_400px_Darkmode.svg)](https://developers.openai.com/codex)

[![Image 151: VT Code](https://agentskills.io/images/logos/vtcode/vt_code_light.svg)![Image 152: VT Code](https://agentskills.io/images/logos/vtcode/vt_code_dark.svg)](https://github.com/vinhnx/vtcode)

[![Image 153: Google AI Edge Gallery](https://agentskills.io/images/logos/google-ai-edge-gallery/google-ai-edge-gallery-light.svg)![Image 154: Google AI Edge Gallery](https://agentskills.io/images/logos/google-ai-edge-gallery/google-ai-edge-gallery-dark.svg)](https://github.com/google-ai-edge/gallery)

[![Image 155: Amp](https://agentskills.io/images/logos/amp/amp-logo-light.svg)![Image 156: Amp](https://agentskills.io/images/logos/amp/amp-logo-dark.svg)](https://ampcode.com/)

[![Image 157: Laravel Boost](https://agentskills.io/images/logos/laravel-boost/boost-light-mode.svg)![Image 158: Laravel Boost](https://agentskills.io/images/logos/laravel-boost/boost-dark-mode.svg)](https://github.com/laravel/boost)

[![Image 159: TRAE](https://agentskills.io/images/logos/trae/trae-logo-lightmode.svg)![Image 160: TRAE](https://agentskills.io/images/logos/trae/trae-logo-darkmode.svg)](https://trae.ai/)

[![Image 161: Pulumi Neo](https://agentskills.io/images/logos/pulumi-neo/pulumi-neo-logo-light.svg)![Image 162: Pulumi Neo](https://agentskills.io/images/logos/pulumi-neo/pulumi-neo-logo-dark.svg)](https://www.pulumi.com/product/neo/)

[![Image 163: VS Code](https://agentskills.io/images/logos/vscode/vscode.svg)![Image 164: VS Code](https://agentskills.io/images/logos/vscode/vscode-alt.svg)](https://code.visualstudio.com/)

[![Image 165: Claude Code](https://agentskills.io/images/logos/claude-code/Claude-Code-logo-Slate.svg)![Image 166: Claude Code](https://agentskills.io/images/logos/claude-code/Claude-Code-logo-Ivory.svg)](https://claude.ai/code)

[![Image 167: OpenCode](https://agentskills.io/images/logos/opencode/opencode-wordmark-light.svg)![Image 168: OpenCode](https://agentskills.io/images/logos/opencode/opencode-wordmark-dark.svg)](https://opencode.ai/)

[![Image 169: Command Code](https://agentskills.io/images/logos/command-code/command-code-logo-for-light.svg)![Image 170: Command Code](https://agentskills.io/images/logos/command-code/command-code-logo-for-dark.svg)](https://commandcode.ai/)

[![Image 171: OpenHands](https://agentskills.io/images/logos/openhands/openhands-logo-light.svg)![Image 172: OpenHands](https://agentskills.io/images/logos/openhands/openhands-logo-dark.svg)](https://openhands.dev/)

[![Image 173: Ona](https://agentskills.io/images/logos/ona/ona-wordmark-light.svg)![Image 174: Ona](https://agentskills.io/images/logos/ona/ona-wordmark-dark.svg)](https://ona.com/)

[![Image 175: Mux](https://agentskills.io/images/logos/mux/mux-editor-light.svg)![Image 176: Mux](https://agentskills.io/images/logos/mux/mux-editor-dark.svg)](https://mux.coder.com/)

## Open development

The Agent Skills format was originally developed by [Anthropic](https://www.anthropic.com/), released as an open standard, and has been adopted by a growing number of agent products. The standard is open to contributions from the broader ecosystem.Come join the discussion on [GitHub](https://github.com/agentskills/agentskills) or [Discord](https://discord.gg/MKPE9g8aUy)!

## Get started with Agent Skills
