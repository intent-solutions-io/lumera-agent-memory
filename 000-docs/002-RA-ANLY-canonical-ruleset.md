# Canonical Ruleset: Plugins + Skills Standards

**Document ID**: 002-RA-ANLY-canonical-ruleset
**Version**: 1.0.0
**Status**: AUTHORITATIVE - Extracted from MASTER Specs
**Created**: 2025-12-20
**Sources**:
- `/claude-code-plugins/000-docs/6767-a-SPEC-MASTER-claude-code-plugins-standard.md`
- `/claude-code-plugins/000-docs/6767-b-SPEC-MASTER-claude-skills-standard.md`

---

## A. PLUGINS STANDARD (6767-a)

### A1. Required Files & Structure

#### MUST Have
- `.claude-plugin/` directory at plugin root
- `.claude-plugin/plugin.json` (manifest file)
- **ONLY `plugin.json` in `.claude-plugin/`** - no other files permitted

#### SHOULD Have (Recommended)
- `LICENSE` - License file
- `README.md` - Documentation
- `CHANGELOG.md` - Version history

#### Component Directories (Optional, Create Only If Used)
- `commands/` - Slash commands (`.md` files)
- `agents/` - Subagent definitions (`.md` files with frontmatter)
- `skills/` - Skills (each in `skill-name/SKILL.md` subdirectory structure)
- `hooks/` - Hook configurations (`hooks.json`)
- `scripts/` - Helper scripts
- `.mcp.json` OR `mcpServers` field in plugin.json - MCP server config

**CRITICAL LAYOUT RULES**:
1. `.claude-plugin/` contains **ONLY** `plugin.json`
2. All component directories at plugin root (NOT inside `.claude-plugin/`)
3. Only create directories you use (NO empty placeholders)
4. Skills require `SKILL.md` in each skill's own subdirectory

### A2. Plugin Manifest Schema (plugin.json)

#### Required Fields

| Field | Type | Constraint | Example |
|-------|------|------------|---------|
| `name` | string | Kebab-case, no spaces, max 64 chars | `"deployment-tools"` |

**Validation Rules**:
- Name MUST be kebab-case
- Name MUST NOT contain spaces
- Name MUST be max 64 characters
- Name MUST be unique within marketplace

#### Recommended Metadata Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `version` | string | Semantic version (MAJOR.MINOR.PATCH) | `"2.1.0"` |
| `description` | string | Brief explanation of purpose | `"Deployment automation tools"` |
| `author` | object | Author information | `{"name": "Dev Team"}` |
| `author.name` | string | Author/team name | `"DevTools Team"` |
| `author.email` | string | Contact email | `"team@example.com"` |
| `author.url` | string | Author website/profile | `"https://github.com/author"` |
| `homepage` | string | Documentation URL | `"https://docs.example.com"` |
| `repository` | string | Source code URL | `"https://github.com/org/plugin"` |
| `license` | string | SPDX license identifier | `"MIT"`, `"Apache-2.0"` |
| `keywords` | array | Discovery/categorization tags | `["testing", "automation"]` |

#### Component Path Fields (Optional)

| Field | Type | Description | Default Behavior |
|-------|------|-------------|------------------|
| `commands` | string \| array | Additional command paths | Supplements `commands/` |
| `agents` | string \| array | Additional agent paths | Supplements `agents/` |
| `hooks` | string \| object | Hook config path or inline | Supplements `hooks/hooks.json` |
| `mcpServers` | string \| object | MCP config path or inline | Supplements `.mcp.json` |

**Critical**: Custom paths **SUPPLEMENT** default directories—they don't replace them.

#### Environment Variables in Manifest

MUST use `${CLAUDE_PLUGIN_ROOT}` for portable paths:

```json
{
  "mcpServers": {
    "database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "DATA_DIR": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    }
  }
}
```

### A3. Naming Conventions (REQUIRED)

| Element | Convention | Example | Validation |
|---------|------------|---------|------------|
| Plugin folder | kebab-case | `deployment-tools/` | MUST |
| Plugin name (manifest) | kebab-case | `"deployment-tools"` | MUST |
| Command files | kebab-case.md | `run-tests.md` | MUST |
| Agent files | kebab-case.md | `security-reviewer.md` | MUST |
| Skill directories | kebab-case/ | `code-analysis/` | MUST |
| Scripts | kebab-case.* | `validate-config.sh` | MUST |

### A4. Component Specifications

#### Commands (Slash Commands)

**Location**: `commands/` directory
**Format**: Markdown files with optional frontmatter

**Frontmatter Fields** (Optional):
- `description`: String - Command description
- `allowed-tools`: String - CSV tool list (e.g., `"Bash(kubectl:*),Bash(docker:*),Read,Glob"`)

**Invocation**: User types `/command-name` (derived from filename without .md)

#### Agents (Subagents)

**Location**: `agents/` directory
**Format**: Markdown files with YAML frontmatter

**REQUIRED Frontmatter Fields**:
| Field | Required | Description |
|-------|----------|-------------|
| `name` | YES | Agent identifier |
| `description` | YES | When Claude should delegate to this agent |

**OPTIONAL Frontmatter Fields**:
| Field | Description | Default |
|-------|-------------|---------|
| `tools` | Comma-separated tool list | Inherits all |
| `model` | `sonnet`, `opus`, `haiku`, `inherit` | inherit |
| `permissionMode` | Permission mode | (system default) |
| `skills` | Skills to auto-load | (none) |

#### Hooks

**Location**: `hooks/hooks.json` or inline in `plugin.json`
**Format**: JSON configuration

**Hook Events**:
| Event | Matcher Required | Use Case |
|-------|------------------|----------|
| `PreToolUse` | Yes | Validate/modify tool inputs |
| `PostToolUse` | Yes | Process results, trigger actions |
| `PermissionRequest` | Yes | Auto-approve/deny permissions |
| `UserPromptSubmit` | No | Add context to prompts |
| `Stop` | No | Prevent premature stops |
| `SubagentStop` | No | Control subagent completion |
| `SessionStart` | Yes | Initialize environment |
| `SessionEnd` | No | Cleanup operations |
| `PreCompact` | Yes | Before context compaction |
| `Notification` | Optional | Handle notifications |

**Hook Types**:
- `command`: Execute bash command
- `prompt`: LLM-based evaluation

**Hook Output (JSON)** MUST include:
```json
{
  "continue": true,
  "stopReason": "Optional reason to stop",
  "suppressOutput": false,
  "systemMessage": "Message shown to user",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "Reason for decision",
    "updatedInput": { "modified_field": "new_value" }
  }
}
```

### A5. Marketplace Schema

#### marketplace.json Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Marketplace identifier (kebab-case) |
| `owner` | object | Marketplace maintainer info |
| `plugins` | array | List of available plugins |

#### Plugin Entry Schema

Required for each plugin in marketplace:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Plugin name |
| `source` | string \| object | **REQUIRED** Where to fetch the plugin |

Optional fields (inherit from plugin.json if present):
- `description`, `version`, `author`, `license`, `keywords`
- `category`: Plugin category for organization
- `tags`: Additional discovery tags
- `strict`: Boolean - require plugin.json in source (default: `true`)

#### Source Types

1. **Relative Path**: `"source": "./plugins/local-plugin"`
2. **GitHub**: `{"source": "github", "repo": "owner/plugin-repo"}`
3. **Git URL**: `{"source": "git", "url": "https://gitlab.com/team/plugin.git"}`
4. **Local Directory**: `{"source": "directory", "path": "/path/to/local/plugin"}`

### A6. Security Requirements (MANDATORY)

#### Minimal Permissions Principle (MUST)

**MUST**:
- Only request tools you actually need
- Scope bash commands: `Bash(git:*)`, `Bash(npm run test:*)`
- Use environment variables for secrets
- Sanitize all inputs
- Set timeouts on hooks
- Use `${CLAUDE_PLUGIN_ROOT}` for all paths

**MUST NOT**:
- Grant unrestricted `Bash` access
- Hardcode credentials
- Pass unvalidated user input to shell
- Allow network calls without timeout
- Perform file operations outside project
- Hardcode API keys in plugin files
- Store secrets in plugin.json
- Log sensitive data

#### Security Audit Checklist (REQUIRED Before Publishing)

- [ ] No hardcoded secrets or API keys
- [ ] All bash commands are scoped appropriately
- [ ] Scripts validate and sanitize inputs
- [ ] Network calls have timeouts
- [ ] File paths use `${CLAUDE_PLUGIN_ROOT}`
- [ ] No path traversal vulnerabilities (`..` not in user inputs)
- [ ] Sensitive files excluded (`.env`, credentials)
- [ ] Dependencies are from trusted sources
- [ ] MCP servers don't expose sensitive data

### A7. Versioning (REQUIRED)

**Semantic Versioning**:
```
MAJOR.MINOR.PATCH
  │     │     └── Bug fixes, documentation
  │     └──────── New features, backward-compatible
  └────────────── Breaking changes
```

**Deprecation Process**:
1. Mark deprecated in description: `"[DEPRECATED] Old command..."`
2. Keep working for one minor version
3. Remove in next major version

### A8. Production-Readiness Checklist (MANDATORY)

#### Manifest
- [ ] `name` is kebab-case, unique, descriptive
- [ ] `version` follows semver
- [ ] `description` clearly explains purpose
- [ ] `author` information is complete
- [ ] `license` specified (SPDX identifier)
- [ ] `keywords` aid discovery
- [ ] `repository` points to source

#### Components
- [ ] All commands documented
- [ ] Agents have clear descriptions
- [ ] Skills follow standard schema (see Section B)
- [ ] Hooks have appropriate matchers
- [ ] MCP servers use `${CLAUDE_PLUGIN_ROOT}`

#### Security
- [ ] No hardcoded secrets
- [ ] Bash commands appropriately scoped
- [ ] Inputs validated/sanitized
- [ ] Timeouts configured
- [ ] Paths are relative with `${CLAUDE_PLUGIN_ROOT}`

#### Testing
- [ ] Plugin loads without errors (`claude --debug`)
- [ ] Commands execute correctly
- [ ] Agents respond appropriately
- [ ] Hooks fire on expected events
- [ ] MCP servers initialize

#### Documentation
- [ ] README explains installation
- [ ] README documents usage
- [ ] README lists requirements
- [ ] CHANGELOG tracks versions
- [ ] Environment variables documented

#### Marketplace
- [ ] Marketplace entry complete
- [ ] Source URL accessible
- [ ] Version matches plugin.json
- [ ] Keywords appropriate

---

## B. SKILLS STANDARD (6767-b)

### B1. Directory Structure (REQUIRED)

```
skill-name/
├── SKILL.md              # REQUIRED
├── scripts/              # OPTIONAL - Executable code
│   ├── analyze.py
│   └── validate.py
├── references/           # OPTIONAL - Docs loaded into context
│   ├── API_REFERENCE.md
│   └── EXAMPLES.md
├── assets/               # OPTIONAL - Templates
│   └── report_template.md
└── LICENSE.txt           # OPTIONAL
```

### B2. Skill Discovery & Location

**Where Skills Live** (Priority Order):

| Location | Scope | Priority | Notes |
|----------|-------|----------|-------|
| `~/.claude/skills/` | Personal (all projects) | 1 (lowest) | Global user skills |
| `.claude/skills/` | Project-specific | 2 | Project scope |
| Plugin `skills/` directory | Plugin-bundled | 3 | Inside plugins |
| Built-in skills | Platform-provided | 4 (highest) | System skills |

**Conflict Resolution**: Later sources override earlier ones when names conflict.

### B3. Naming Conventions (REQUIRED)

**Folder Names**:
- SHOULD match `name` field for clarity
- Use **gerund form** (verb + -ing): `processing-pdfs`, `analyzing-spreadsheets`
- Alternatives: noun phrases (`pdf-processing`), action-oriented (`process-pdfs`)

**AVOID**:
- Vague: `helper`, `utils`, `tools`
- Generic: `documents`, `data`, `files`
- Reserved: `anthropic-*`, `claude-*`

**Constraint**: Lowercase letters, numbers, hyphens only

### B4. SKILL.md Frontmatter (YAML)

#### REQUIRED Fields

| Field | Type | Max Length | Constraints | Purpose |
|-------|------|------------|-------------|---------|
| `name` | string | 64 chars | Lowercase, numbers, hyphens only. NO XML tags. NO `anthropic` or `claude`. | Command identifier |
| `description` | string | 1024 chars | Third person voice. NO XML tags. Non-empty. | Skill selection signal |

**Description Formula**:
```
[Primary capabilities]. [Secondary features]. Use when [scenarios]. Trigger with "[phrases]".
```

**Good Description Examples**:
```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.

description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.
```

**Bad Description Examples**:
```yaml
description: Helps with documents          # Too vague
description: I can process your PDFs       # Wrong voice (first person)
description: You can use this for data     # Wrong voice (second person)
```

#### OPTIONAL Fields (Anthropic Spec)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `allowed-tools` | CSV string | No pre-approved tools | Pre-approve tools for skill execution |
| `model` | string | `"inherit"` | Override session model |
| `version` | string (semver) | - | Version tracking |
| `license` | string | - | License terms |
| `mode` | boolean | `false` | Categorize as "mode command" |
| `disable-model-invocation` | boolean | `false` | Remove from auto-discovery |

**`allowed-tools` Syntax**:
```yaml
# Multiple tools (comma-separated)
allowed-tools: "Read,Write,Glob,Grep,Edit"

# Scoped bash commands
allowed-tools: "Bash(git status:*),Bash(git diff:*),Read,Grep"

# NPM-scoped
allowed-tools: "Bash(npm:*),Bash(npx:*),Read,Write"

# Read-only
allowed-tools: "Read,Glob,Grep"
```

**Security Principle**: Grant ONLY tools the skill requires. Over-specifying = unnecessary attack surface.

**`model` Values**:
- `inherit` - Use session model (default)
- `"claude-opus-4-*"` - Force Opus
- `"claude-sonnet-4-*"` - Force Sonnet
- `"claude-haiku-*"` - Force Haiku

**`disable-model-invocation`**:
- `true` - Manual invocation only (via `/skill-name`)
- `false` - Auto-discovery enabled (default)

Use `true` for:
- Destructive operations (delete files, drop databases)
- Production deployments
- Operations requiring explicit confirmation

#### ENTERPRISE Extension Fields (Intent Solutions Marketplace)

**REQUIRED for Marketplace Submission**:

| Field | Type | Format | Example |
|-------|------|--------|---------|
| `author` | string | `Name <email>` or `Name` | `"Jeremy Longshore <jeremy@intentsolutions.io>"` |
| `version` | string | Semver | `"1.0.0"` |
| `license` | string | SPDX identifier | `"MIT"` |
| `allowed-tools` | CSV string | Tool list | `"Read,Write,Bash(git:*)"` |

**RECOMMENDED**:

| Field | Type | Example |
|-------|------|---------|
| `tags` | array | `["devops", "kubernetes", "deployment"]` |

**Enterprise Required Fields Summary**:

| Field | Anthropic Spec | Enterprise Required |
|-------|----------------|---------------------|
| `name` | Required | Required |
| `description` | Required | Required |
| `allowed-tools` | Optional | **Required** |
| `version` | Optional | **Required** |
| `author` | Not in spec | **Required** |
| `license` | Optional | **Required** |
| `tags` | Not in spec | Recommended |

### B5. SKILL.md Body Structure (REQUIRED)

**Maximum Size**: 500 lines
**Token Budget**: Target ~2,500 tokens, max 5,000 tokens

**Required Sections**:

```markdown
# [Skill Name]

[1-2 sentence purpose statement]

## Overview

[What this skill does, when to use it, key capabilities - 3-5 sentences]

## Prerequisites

**Required**:
- [Tool/API/package 1]

**Environment Variables**:
- `ENV_VAR`: [Description]

**Optional**:
- [Nice-to-have]

## Instructions

### Step 1: [Action Verb]
[Imperative instructions]

### Step 2: [Action Verb]
[More instructions]

## Output

This skill produces:
- [Artifact 1]
- [Artifact 2]

## Error Handling

**Common Failures** (MINIMUM 4):

1. **Error**: [Error message]
   **Cause**: [Why]
   **Solution**: [Fix]

## Examples

### Example 1: [Scenario]
**Input**: [Input data]
**Output**: [Expected output]

### Example 2: [Advanced Scenario]
[Another example]

## Resources

- Reference: `{baseDir}/references/API_DOCS.md`
- Script: `{baseDir}/scripts/validate.py`
```

**Content Guidelines** (MANDATORY):

| Guideline | Requirement |
|-----------|-------------|
| **Size Limit** | Keep SKILL.md body under **500 lines** |
| **Token Budget** | Target ~2,500 tokens, max 5,000 tokens |
| **Language** | Use **imperative voice** ("Analyze data", not "You should analyze") |
| **Paths** | Always use `{baseDir}` variable, NEVER hardcode absolute paths |
| **Examples** | Include at least **2-3 concrete examples** with input/output |
| **Error Handling** | Document **4+ common failures** with solutions |
| **Voice** | Third person in descriptions, imperative in instructions |
| **References** | One-level-deep only (no nested chains) |

### B6. Progressive Disclosure (When >400 Lines)

**Critical Rule**: One-level-deep references only.

**AVOID**:
```
SKILL.md → advanced.md → details.md → actual_info.md  ❌
```

**GOOD**:
```
SKILL.md → advanced.md  ✅
SKILL.md → reference.md  ✅
SKILL.md → examples.md  ✅
```

### B7. Security Requirements (MANDATORY)

#### Choosing `allowed-tools` Conservatively

**Good Examples**:
```yaml
# Read-only audit
allowed-tools: "Read,Glob,Grep"

# File transformation
allowed-tools: "Read,Write,Edit"

# Git operations only
allowed-tools: "Bash(git:*),Read,Grep"
```

**Bad Examples**:
```yaml
# Overly permissive
allowed-tools: "Bash,Read,Write,Edit,Glob,Grep,WebSearch,Task,Agent"

# Unscoped bash
allowed-tools: "Bash"
```

#### Security Considerations (MANDATORY Before Use)

**CRITICAL**: Only use Skills from trusted sources.

**Before using untrusted skill**:
- [ ] Review all bundled files
- [ ] Check for unusual network calls
- [ ] Inspect scripts for malicious code
- [ ] Verify tool invocations match stated purpose
- [ ] Validate external URLs (if any)

**Malicious skills could**:
- Exfiltrate data via network calls
- Access unauthorized files
- Misuse tools (Bash for system manipulation)
- Inject instructions overriding safety guidelines

### B8. Version Control & Deprecation

**Semantic Versioning**:
```
MAJOR.MINOR.PATCH
  │     │     └── Bug fixes, clarifications
  │     └──────── New features, additive changes
  └────────────── Breaking changes to interface
```

**Deprecation Strategy**:
1. Add deprecation notice: `description: "[DEPRECATED - Use new-skill instead] ..."`
2. Set `disable-model-invocation: true` to prevent auto-activation
3. Keep available for manual invocation during transition
4. Remove entirely in next major version

### B9. Production-Readiness Checklist (MANDATORY)

#### Naming & Description
- [ ] `name` matches folder name (lowercase + hyphens)
- [ ] `name` is under 64 characters
- [ ] `description` under 1024 characters
- [ ] `description` uses third person voice
- [ ] `description` includes what + when + trigger phrases
- [ ] No reserved words (`anthropic`, `claude`)

#### Structure & Tools
- [ ] SKILL.md at root of skill folder
- [ ] Body under 500 lines
- [ ] Uses `{baseDir}` for all paths
- [ ] No hardcoded absolute paths
- [ ] `allowed-tools` includes only necessary tools
- [ ] Forward slashes in all paths (not backslashes)

#### Instructions Quality
- [ ] Has all required sections
- [ ] Uses imperative voice
- [ ] 2-3 concrete examples with input/output
- [ ] 4+ common errors documented with solutions
- [ ] One-level-deep file references only

#### Enterprise Requirements (Marketplace)
- [ ] `author` field present and formatted correctly
- [ ] `version` field present (semver)
- [ ] `license` field present (SPDX identifier)
- [ ] `allowed-tools` field present (not optional)
- [ ] `tags` field present (recommended)

#### Testing
- [ ] Tested with Haiku, Sonnet, and Opus
- [ ] Trigger phrases activate skill correctly
- [ ] Scripts execute without errors
- [ ] Examples produce expected output
- [ ] No false positive activations

---

## C. MARKETPLACE COMPLIANCE REQUIREMENTS

### C1. Marketplace Configuration

**marketplace.json Schema**:

**REQUIRED Fields**:
- `name`: Marketplace identifier (kebab-case)
- `owner`: Object with `name` and `email`
- `plugins`: Array of plugin entries

**Optional Metadata**:
- `metadata.description`: Marketplace description
- `metadata.version`: Marketplace version
- `metadata.pluginRoot`: Base path for relative sources

### C2. Plugin Entry Requirements

Each plugin entry MUST include:
- `name`: Plugin name
- `source`: Where to fetch (REQUIRED)

All other fields (description, version, author, license, keywords) are:
- Optional if `strict: true` (default) - inherit from plugin.json
- Required if `strict: false` - marketplace entry serves as manifest

### C3. Trust & Security Warning (REQUIRED)

**From Official Docs**:
> ⚠️ **Trust Warning**: Users must trust plugins before installing. Anthropic does not control MCP servers, files, or included software, and cannot verify intended functionality or future changes.

This warning MUST be displayed in marketplace documentation.

---

## D. CI REQUIREMENTS

### D1. Validation Checks (MANDATORY)

CI MUST validate:

1. **Manifest Validation**:
   - plugin.json exists at `.claude-plugin/plugin.json`
   - ONLY plugin.json in `.claude-plugin/` (no other files)
   - `name` field present
   - `name` is kebab-case
   - `name` max 64 characters
   - `version` follows semver (if present)

2. **Structure Validation**:
   - Component directories NOT inside `.claude-plugin/`
   - Skills have `SKILL.md` in each subdirectory
   - No empty placeholder directories

3. **Skills Validation** (for each skill):
   - `SKILL.md` exists at skill root
   - YAML frontmatter present and valid
   - `name` field present
   - `name` is lowercase + hyphens only
   - `name` max 64 characters
   - `description` field present
   - `description` max 1024 characters
   - `description` uses third person voice
   - Body under 500 lines
   - No hardcoded absolute paths (must use `{baseDir}`)
   - Forward slashes in all paths

4. **Enterprise Requirements** (if marketplace submission):
   - Skills have `author` field
   - Skills have `version` field (semver)
   - Skills have `license` field
   - Skills have `allowed-tools` field

5. **Security Validation**:
   - No hardcoded secrets (scan for patterns)
   - No hardcoded API keys
   - Paths use `${CLAUDE_PLUGIN_ROOT}` or `{baseDir}`
   - No `.env` files committed
   - No credential files committed

6. **Naming Validation**:
   - All kebab-case filenames
   - No uppercase in plugin/skill/command/agent names
   - No reserved words (`anthropic`, `claude`)

### D2. CI Gates (REQUIRED)

**PR Validation** (MUST pass to merge):
- [ ] Manifest validation
- [ ] Structure validation
- [ ] Skills schema validation
- [ ] Security scans
- [ ] Naming convention checks
- [ ] Enterprise requirements (if marketplace)

**Main Branch Protection** (MUST pass):
- All PR checks
- Version tag matches manifest
- CHANGELOG updated
- No regressions

### D3. Failure Reporting (REQUIRED)

Validator MUST produce:
- **File path** where error occurred
- **Exact field** that failed
- **Expected value/format**
- **Actual value found**
- **Fix recommendation**

Example error output:
```
❌ SKILL.md Validation Failed

File: skills/processing-pdfs/SKILL.md
Field: description (frontmatter)
Error: Uses first person voice
Expected: Third person voice ("Extract PDFs...")
Actual: "I can process your PDFs..."
Fix: Rewrite description in third person
```

---

## E. NON-NEGOTIABLE CONSTRAINTS

### E1. MUST Requirements (Plugins)

**Manifest**:
- MUST have `.claude-plugin/plugin.json`
- MUST have `name` field in manifest
- MUST use kebab-case for `name`
- MUST keep `name` under 64 characters
- MUST have ONLY plugin.json in `.claude-plugin/`

**Structure**:
- Component directories MUST be at plugin root
- Component directories MUST NOT be inside `.claude-plugin/`
- Skills MUST have `SKILL.md` in each subdirectory

**Security**:
- MUST NOT hardcode secrets
- MUST NOT commit API keys
- MUST use `${CLAUDE_PLUGIN_ROOT}` for all plugin paths
- MUST scope bash commands (if using Bash tool)
- MUST validate/sanitize all inputs

**Versioning**:
- MUST follow semver if `version` field present
- MUST update CHANGELOG for releases

### E2. MUST Requirements (Skills)

**File Structure**:
- MUST have `SKILL.md` at skill root
- MUST have YAML frontmatter in SKILL.md

**Frontmatter**:
- MUST have `name` field
- MUST have `description` field
- `name` MUST be lowercase + hyphens only
- `name` MUST be max 64 characters
- `description` MUST be max 1024 characters
- `description` MUST use third person voice
- `description` MUST be non-empty
- MUST NOT contain XML tags in `name` or `description`
- MUST NOT use reserved words (`anthropic`, `claude`) in `name`

**Body**:
- MUST be under 500 lines
- MUST use imperative voice in instructions
- MUST use `{baseDir}` for all paths (NO hardcoded absolutes)
- MUST use forward slashes in paths
- MUST include at least 2 examples
- MUST document at least 4 common errors
- MUST use one-level-deep references only

**Enterprise Requirements** (marketplace submission):
- MUST have `author` field
- MUST have `version` field (semver)
- MUST have `license` field
- MUST have `allowed-tools` field

### E3. MUST NOT Requirements (Both)

**Security**:
- MUST NOT hardcode secrets
- MUST NOT hardcode API keys
- MUST NOT commit `.env` files
- MUST NOT commit credential files
- MUST NOT use unrestricted `Bash` tool
- MUST NOT use `Bash` without scoping
- MUST NOT log sensitive data

**Paths**:
- MUST NOT use hardcoded absolute paths
- MUST NOT use backslashes in paths
- MUST NOT traverse parent directories without validation

**Naming**:
- MUST NOT use uppercase in names
- MUST NOT use spaces in names
- MUST NOT use reserved words (`anthropic`, `claude`)
- MUST NOT use XML tags in descriptions

**Structure**:
- MUST NOT put files other than plugin.json in `.claude-plugin/`
- MUST NOT nest skills deeper than one level for references

---

## F. COMPLIANCE CHECKLIST

### F1. New Plugin Checklist

- [ ] Created `.claude-plugin/plugin.json` with `name` field
- [ ] `name` is kebab-case, unique, under 64 chars
- [ ] ONLY plugin.json in `.claude-plugin/` directory
- [ ] Component directories at plugin root (not in `.claude-plugin/`)
- [ ] Created README.md with installation/usage
- [ ] Created LICENSE file
- [ ] Created CHANGELOG.md
- [ ] All filenames are kebab-case
- [ ] No empty placeholder directories
- [ ] Tested locally with `claude --debug`
- [ ] Plugin loads without errors

### F2. Skill Compliance Checklist

**Anthropic Spec Compliance**:
- [ ] `name`: lowercase + hyphens, under 64 chars
- [ ] `description`: third person, under 1024 chars, includes what + when + triggers
- [ ] No reserved words (`anthropic`, `claude`)
- [ ] Body under 500 lines
- [ ] Uses `{baseDir}` for all paths
- [ ] Forward slashes in all paths
- [ ] 2-3 examples with input/output
- [ ] 4+ errors documented with solutions
- [ ] One-level-deep references only
- [ ] Tested with multiple models

**Enterprise Spec Compliance** (marketplace):
- [ ] `author` field present and formatted
- [ ] `version` field present (semver)
- [ ] `license` field present (SPDX)
- [ ] `allowed-tools` field present (not optional)
- [ ] `tags` field present (recommended)

### F3. Security Compliance Checklist

- [ ] No hardcoded secrets or API keys
- [ ] Bash commands appropriately scoped
- [ ] Scripts validate and sanitize inputs
- [ ] Network calls have timeouts (if applicable)
- [ ] Paths use `${CLAUDE_PLUGIN_ROOT}` or `{baseDir}`
- [ ] No path traversal vulnerabilities
- [ ] `.env` not committed
- [ ] Credential files not committed
- [ ] Dependencies from trusted sources
- [ ] MCP servers don't expose sensitive data
- [ ] `allowed-tools` lists only necessary tools

### F4. Documentation Compliance Checklist

- [ ] README explains installation
- [ ] README documents usage
- [ ] README lists requirements
- [ ] README documents environment variables
- [ ] CHANGELOG tracks versions
- [ ] LICENSE file present
- [ ] All examples produce expected output
- [ ] Error handling documented

### F5. Marketplace Compliance Checklist

- [ ] Marketplace entry complete
- [ ] Source URL accessible
- [ ] Version matches manifest
- [ ] Keywords appropriate
- [ ] Category assigned
- [ ] Trust warning displayed
- [ ] Description accurate
- [ ] Author information complete

### F6. CI Validation Checklist

- [ ] Manifest validation passes
- [ ] Structure validation passes
- [ ] Skills schema validation passes
- [ ] Security scans pass
- [ ] Naming convention checks pass
- [ ] Enterprise requirements pass (if applicable)
- [ ] No regressions detected
- [ ] All tests pass

---

## G. VALIDATION SUMMARY

### Critical Validations (MUST Pass)

1. **Manifest Schema**: plugin.json valid, `name` field present, kebab-case
2. **Directory Structure**: `.claude-plugin/` contains ONLY plugin.json
3. **Skills Schema**: YAML frontmatter valid, required fields present
4. **Security**: No hardcoded secrets, proper path usage
5. **Naming**: All kebab-case, no reserved words
6. **Documentation**: README, LICENSE, CHANGELOG present
7. **Enterprise** (if marketplace): author, version, license, allowed-tools, tags

### Validation Errors to Catch

| Error | Severity | Example |
|-------|----------|---------|
| Missing plugin.json | CRITICAL | `.claude-plugin/plugin.json` not found |
| Extra files in .claude-plugin/ | CRITICAL | `.claude-plugin/README.md` detected |
| Missing `name` field | CRITICAL | plugin.json has no `name` |
| Invalid naming | CRITICAL | `MyPlugin` instead of `my-plugin` |
| Missing SKILL.md | CRITICAL | `skills/pdf-processing/` has no SKILL.md |
| Missing frontmatter | CRITICAL | SKILL.md has no YAML block |
| Hardcoded paths | HIGH | `/home/user/plugin/` instead of `${CLAUDE_PLUGIN_ROOT}` |
| Hardcoded secrets | CRITICAL | `API_KEY="sk-..."` detected |
| Wrong voice | MEDIUM | "I can process" instead of "Processes" |
| Over 500 lines | MEDIUM | SKILL.md is 612 lines |
| Missing enterprise fields | HIGH | No `author` field for marketplace submission |

---

**END OF CANONICAL RULESET**

This document represents the complete extraction of requirements from both MASTER specifications. All plugin and skill development MUST comply with these rules.
