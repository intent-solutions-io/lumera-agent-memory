# 009-DR-GUID-validation-and-ci.md

**Document Type**: Operator Guide (DR-GUID)
**Subject**: Standards Validation & CI Integration
**Version**: 1.0.0
**Date**: 2025-12-20
**Author**: Claude Code (Lumera Standards Enforcement)

---

## Purpose

This document provides operator instructions for running standards validation locally and understanding CI enforcement gates. It ensures all plugins and skills comply with MASTER specifications (6767-a and 6767-b) before code reaches production.

---

## Table of Contents

1. [Running Validator Locally](#running-validator-locally)
2. [CI Workflows Overview](#ci-workflows-overview)
3. [Common Validation Errors](#common-validation-errors)
4. [Development Workflow Integration](#development-workflow-integration)
5. [Troubleshooting](#troubleshooting)
6. [References](#references)

---

## Running Validator Locally

### Prerequisites

```bash
# Ensure you're in the plugin directory
cd /home/jeremy/000-projects/Lumera-Emanuel/plugins/lumera-agent-memory

# Install dependencies (if not already done)
pip install -r scripts/requirements.txt
```

### Basic Usage

**Anthropic Mode** (validates against official Anthropic requirements only):

```bash
python scripts/validate_standards.py --plugin-root .
```

**Enterprise Mode** (validates against Intent Solutions marketplace requirements):

```bash
python scripts/validate_standards.py --plugin-root . --enterprise
```

**Verbose Mode** (shows detailed validation steps):

```bash
python scripts/validate_standards.py --plugin-root . --verbose
```

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | All validations passed | Proceed with commit/PR |
| `1` | CRITICAL or HIGH errors found | Must fix before committing |
| `2` | Only MEDIUM or LOW warnings | Can commit, but should fix |

### Example Output

**Success**:
```
Running standards validation...
✓ Plugin manifest valid
✓ Directory structure correct
✓ All 3 skills validated
✓ Security checks passed
✓ Naming conventions correct

SUCCESS: All validations passed (Anthropic mode)
```

**Failure**:
```
Running standards validation...
✓ Plugin manifest valid
✗ Directory structure issues found
✗ 2 skills failed validation

ERRORS FOUND:

[CRITICAL] .claude-plugin/README.md
  Field: extra_files_in_claude_plugin
  Expected: Only plugin.json in .claude-plugin/
  Actual: Found README.md
  Fix: Remove all files except plugin.json from .claude-plugin/ directory

[HIGH] skills/data-analysis/SKILL.md
  Field: allowed-tools
  Expected: CSV string (e.g., "Read,Write,Bash")
  Actual: YAML array format
  Fix: Change frontmatter to: allowed-tools: "Read,Write,Bash"

FAILED: 2 errors found (1 CRITICAL, 1 HIGH)
```

---

## CI Workflows Overview

### PR Validation Workflow (`.github/workflows/pr.yml`)

**Trigger**: Every pull request to `main` branch

**Steps**:
1. **Checkout code**
2. **Setup Python 3.10**
3. **Install dependencies**
4. **Validate standards compliance** ⬅️ BLOCKING GATE
   - Runs in Anthropic mode
   - Fails PR on CRITICAL or HIGH errors
   - Must pass before other tests run
5. **Run security tests** (redaction, encryption)
6. **Run component tests** (cascade, index)
7. **Run 90-second smoke test**
8. **Lint check** (black, isort, flake8)

**Blocking Behavior**:
- Standards validation runs FIRST (fail-fast)
- If validation fails, PR cannot merge
- Developer must fix errors locally and push again

**Example PR Status**:
```
✓ Checkout code
✓ Set up Python 3.10
✓ Install dependencies
✗ Validate standards compliance  ← PR BLOCKED HERE
  Expected: CSV string for allowed-tools
  Actual: YAML array format
  See logs for details
```

### Main Branch Workflow (`.github/workflows/main.yml`)

**Trigger**: Every push to `main` branch (post-merge)

**Steps**:
1. **Checkout code**
2. **Setup Python 3.10**
3. **Install dependencies**
4. **Validate standards (Anthropic mode)** ⬅️ GATE 1
5. **Validate standards (Enterprise mode)** ⬅️ GATE 2
   - Runs BOTH validation modes
   - Enterprise mode requires additional fields (author, version, license)
6. **Run all tests with coverage**
7. **Lint and format check**
8. **Upload coverage report**

**Purpose**:
- Comprehensive validation (both modes)
- Ensures main branch always meets highest standards
- Generates coverage reports for monitoring
- Catches issues that might slip through PR review

---

## Common Validation Errors

### ERROR 1: YAML Array Instead of CSV String

**Error Message**:
```
[HIGH] skills/my-skill/SKILL.md
  Field: allowed-tools
  Expected: CSV string (e.g., "Read,Write,Bash")
  Actual: YAML array format
  Fix: Change frontmatter to: allowed-tools: "Read,Write,Bash"
```

**Cause**: Using YAML array syntax instead of CSV string per MASTER spec 6767-b

**Wrong**:
```yaml
---
name: my-skill
description: Example skill
allowed-tools:
  - Read
  - Write
  - Bash
---
```

**Correct**:
```yaml
---
name: my-skill
description: Example skill
allowed-tools: "Read,Write,Bash"
---
```

**Fix**: Edit skill frontmatter, change array to CSV string, run validator again

---

### ERROR 2: Extra Files in .claude-plugin/

**Error Message**:
```
[CRITICAL] .claude-plugin/README.md
  Field: extra_files_in_claude_plugin
  Expected: Only plugin.json in .claude-plugin/
  Actual: Found README.md, config.json
  Fix: Remove all files except plugin.json from .claude-plugin/ directory
```

**Cause**: MASTER spec 6767-a mandates ONLY plugin.json in `.claude-plugin/`

**Fix**:
```bash
cd .claude-plugin
ls -a
# Should show ONLY: . .. plugin.json

# Remove any extra files
rm README.md config.json  # or whatever extra files exist
```

---

### ERROR 3: Non-Kebab-Case Name

**Error Message**:
```
[CRITICAL] .claude-plugin/plugin.json
  Field: name
  Expected: kebab-case (e.g., "my-plugin-name")
  Actual: "My_Plugin_Name"
  Fix: Change name to lowercase with hyphens only
```

**Cause**: Plugin/skill names MUST be kebab-case per MASTER specs

**Wrong**: `"My_Plugin_Name"`, `"myPluginName"`, `"my_plugin_name"`

**Correct**: `"my-plugin-name"`

**Fix**: Edit plugin.json or SKILL.md frontmatter, change name to kebab-case

---

### ERROR 4: Missing Required Fields (Enterprise Mode)

**Error Message**:
```
[HIGH] skills/my-skill/SKILL.md
  Field: author
  Expected: Present (Enterprise mode requirement)
  Actual: Missing
  Fix: Add author: "Your Name <your.email@example.com>"
```

**Cause**: Enterprise mode requires `author`, `version`, `license`, `allowed-tools`

**Fix**:
```yaml
---
name: my-skill
description: Example skill
allowed-tools: "Read,Write,Bash"
author: "Jeremy Longshore <jeremy@intentsolutions.io>"
version: "1.0.0"
license: "MIT"
---
```

---

### ERROR 5: Hardcoded Secrets Detected

**Error Message**:
```
[CRITICAL] src/config.py
  Field: hardcoded_secret
  Expected: No API keys or secrets in code
  Actual: Found potential API key: "sk_live_abcd1234..."
  Fix: Move to environment variable, add to .env.example
```

**Cause**: Security scan detected potential secret in code

**Fix**:
1. Remove secret from code
2. Use environment variable:
   ```python
   import os
   api_key = os.getenv("MY_API_KEY")
   ```
3. Add to `.env.example`:
   ```
   MY_API_KEY=your_key_here
   ```
4. Add `.env` to `.gitignore`

---

### ERROR 6: Invalid Semver Version

**Error Message**:
```
[HIGH] skills/my-skill/SKILL.md
  Field: version
  Expected: Semantic versioning (MAJOR.MINOR.PATCH)
  Actual: "v1.0" or "1.0"
  Fix: Change to "1.0.0"
```

**Cause**: Version must follow MAJOR.MINOR.PATCH format

**Wrong**: `"v1.0"`, `"1.0"`, `"1"`

**Correct**: `"1.0.0"`, `"2.3.1"`

---

### ERROR 7: Hardcoded Absolute Paths in Skills

**Error Message**:
```
[MEDIUM] skills/my-skill/SKILL.md
  Field: paths
  Expected: Use {baseDir} variable
  Actual: Found hardcoded path: /home/user/projects/...
  Fix: Replace with {baseDir}/relative/path
```

**Cause**: Skills must use `{baseDir}` variable per 6767-b spec

**Wrong**: `/home/user/projects/my-plugin/data/config.json`

**Correct**: `{baseDir}/data/config.json`

---

## Development Workflow Integration

### Pre-Commit Hook (Recommended)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

cd plugins/lumera-agent-memory

echo "Running standards validation..."
python scripts/validate_standards.py --plugin-root .

if [ $? -ne 0 ]; then
    echo "❌ Standards validation failed. Commit aborted."
    echo "Fix errors above and try again."
    exit 1
fi

echo "✅ Standards validation passed"
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

### Pre-Push Hook (Alternative)

For faster commits, validate before push instead:

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash

cd plugins/lumera-agent-memory

echo "Running comprehensive standards validation..."
python scripts/validate_standards.py --plugin-root . --enterprise --verbose

if [ $? -ne 0 ]; then
    echo "❌ Standards validation failed. Push aborted."
    exit 1
fi

echo "✅ All validations passed"
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-push
```

### IDE Integration (VS Code)

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Validate Standards",
      "type": "shell",
      "command": "cd plugins/lumera-agent-memory && python scripts/validate_standards.py --plugin-root . --verbose",
      "group": {
        "kind": "test",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ]
}
```

Run via: `Ctrl+Shift+B` → Select "Validate Standards"

---

## Troubleshooting

### Issue: Validator script not found

**Symptom**:
```
python: can't open file 'scripts/validate_standards.py': [Errno 2] No such file or directory
```

**Fix**:
```bash
# Ensure you're in the correct directory
cd /home/jeremy/000-projects/Lumera-Emanuel/plugins/lumera-agent-memory

# Verify file exists
ls -la scripts/validate_standards.py
```

---

### Issue: Import errors when running validator

**Symptom**:
```
ImportError: No module named 'jsonschema'
```

**Fix**:
```bash
# Install requirements
pip install -r scripts/requirements.txt

# Or install individually
pip install jsonschema pyyaml
```

---

### Issue: CI passes but local validation fails

**Symptom**: PR merged but local validator shows errors

**Cause**: Different Python versions or missing dependencies

**Fix**:
```bash
# Match CI Python version
pyenv install 3.10
pyenv local 3.10

# Reinstall dependencies
pip install -r scripts/requirements.txt

# Run validation
python scripts/validate_standards.py --plugin-root .
```

---

### Issue: False positive on secret detection

**Symptom**: Validator flags non-secret as secret

**Example**:
```
[CRITICAL] tests/fixtures/test_data.json
  Field: hardcoded_secret
  Actual: Found potential API key: "test_key_abcd1234..."
```

**Fix**: Add to validator exemptions (if truly a test fixture):
```python
# In validate_standards.py, add to EXEMPT_PATHS
EXEMPT_PATHS = [
    "tests/fixtures/",
    "tests/test_data.json"
]
```

---

### Issue: Validator hangs or takes too long

**Symptom**: Validation runs for >60 seconds

**Cause**: Large files, many skills, or inefficient regex

**Fix**:
```bash
# Run with verbose to see where it hangs
python scripts/validate_standards.py --plugin-root . --verbose

# Check file sizes
find . -type f -size +1M

# Consider excluding large binary files
```

---

## References

### MASTER Specifications

| Document | Location | Purpose |
|----------|----------|---------|
| 6767-a | `/claude-code-plugins/000-docs/6767-a-SPEC-MASTER-claude-code-plugins-standard.md` | Plugin manifest, structure, marketplace |
| 6767-b | `/claude-code-plugins/000-docs/6767-b-SPEC-MASTER-claude-skills-standard.md` | Skills frontmatter, body, validation |

### Derivative Documents (This Repo)

| Document | Location | Purpose |
|----------|----------|---------|
| Canonical Ruleset | `000-docs/001-RA-ANLY-canonical-ruleset.md` | Extracted requirements from MASTER specs |
| Discrepancy Report | `000-docs/002-RA-REPT-standards-discrepancy.md` | Comparison vs Nixtla templates |
| Skills Schema | `000-docs/003-RA-DATA-skills-schema-summary.json` | Machine-readable skills validation rules |
| Plugins Schema | `000-docs/004-RA-DATA-plugins-schema-summary.json` | Machine-readable plugins validation rules |

### Validator Implementation

| File | Purpose |
|------|---------|
| `plugins/lumera-agent-memory/scripts/validate_standards.py` | Main validator script |
| `.github/workflows/pr.yml` | PR validation workflow |
| `.github/workflows/main.yml` | Main branch comprehensive validation |

### External Standards

- **Semantic Versioning**: https://semver.org/
- **SPDX License Identifiers**: https://spdx.org/licenses/
- **Kebab Case**: https://en.wikipedia.org/wiki/Letter_case#Kebab_case

---

## Quick Reference

### One-Line Checks

```bash
# Quick validation (Anthropic mode)
cd plugins/lumera-agent-memory && python scripts/validate_standards.py --plugin-root .

# Comprehensive (Enterprise mode)
cd plugins/lumera-agent-memory && python scripts/validate_standards.py --plugin-root . --enterprise --verbose

# Check CI status
gh pr checks  # (requires GitHub CLI)

# View CI logs
gh run view --log  # (requires GitHub CLI)
```

### Common Commands

```bash
# Fix plugin name
jq '.name = "my-plugin-name"' .claude-plugin/plugin.json > temp.json && mv temp.json .claude-plugin/plugin.json

# Fix skill allowed-tools (manual edit required)
nano skills/my-skill/SKILL.md

# Remove extra files from .claude-plugin/
find .claude-plugin -type f ! -name 'plugin.json' -delete

# Check for hardcoded secrets
grep -r "sk_live_\|AKIA\|-----BEGIN" src/
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-20 | Initial operator guide created |

---

**END OF DOCUMENT**
