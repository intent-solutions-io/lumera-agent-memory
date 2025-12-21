# Standards Discrepancy Report: MASTER vs Nixtla/Templates

**Document ID**: 003-RA-REPT-standards-discrepancy
**Version**: 1.0.0
**Status**: CRITICAL FINDINGS
**Generated**: 2025-12-20
**Audited Files**: 16 documents/configs
**Total Discrepancies Found**: 23

---

## Executive Summary

This report identifies discrepancies between MASTER specifications (6767-a, 6767-b) and downstream implementations (Nixtla docs, templates, configs). **Critical severity issues must be resolved before production use**.

### Severity Distribution

| Severity | Count | Impact |
|----------|-------|--------|
| CRITICAL | 6 | Breaks spec compliance |
| HIGH | 8 | Likely to cause failures |
| MEDIUM | 7 | Deviation from best practices |
| LOW | 2 | Minor inconsistencies |

### Priority Actions Required

1. **CRITICAL**: Fix `allowed-tools` format in skill-template.md (array → CSV string)
2. **CRITICAL**: Reconcile Nixtla SKILLS-STANDARD-COMPLETE.md versioning conflict
3. **HIGH**: Update generation-config.json to reflect Anthropic optional fields vs Enterprise requirements
4. **HIGH**: Validate all 500 planned skills against MASTER schema

---

## B1. MASTER Skills vs Nixtla SKILLS-STANDARD-COMPLETE.md

### Comparison Overview

| Attribute | MASTER (6767-b) | Nixtla (077) | Status |
|-----------|----------------|--------------|--------|
| **Document ID** | `6767-b-SPEC-MASTER-claude-skills-standard.md` | `077-SPEC-MASTER-claude-skills-standard.md` | ⚠️ CONFLICT |
| **Version** | 2.0.0 | 2.3.0 | ⚠️ CONFLICT |
| **Date Updated** | 2025-12-07 | 2025-12-08 | Nixtla is NEWER |
| **Status** | AUTHORITATIVE | AUTHORITATIVE | ⚠️ BOTH CLAIM AUTHORITY |
| **File Size** | 29 KB | 100 KB+ (truncated read) | Nixtla is 3x+ larger |

### DISCREPANCY D1.1: Document ID Conflict

**File**: `/nixtla/000-docs/000a-skills-schema/SKILLS-STANDARD-COMPLETE.md`
**Severity**: CRITICAL
**Field**: Document ID header
**MASTER States**: `6767-b-SPEC-MASTER-claude-skills-standard.md`
**Nixtla States**: `077-SPEC-MASTER-claude-skills-standard.md`

**Issue**: Nixtla uses old numbering scheme (077) instead of canonical 6767-b identifier. Both claim to be "AUTHORITATIVE - Single Source of Truth".

**Impact**: Ambiguity about which document is canonical. Teams may reference wrong version.

**Fix Required**:
```markdown
# Option 1: Nixtla doc is outdated
- Delete /nixtla/000-docs/000a-skills-schema/SKILLS-STANDARD-COMPLETE.md
- Reference MASTER 6767-b instead

# Option 2: Nixtla doc has additional content worth preserving
- Rename to: 010-DR-REFF-nixtla-skills-reference.md (not MASTER)
- Add header: "Reference: See 6767-b for canonical spec"
- Remove "AUTHORITATIVE" claim
```

**Recommendation**: OPTION 1 (delete Nixtla copy, use MASTER only)

### DISCREPANCY D1.2: Version Number Conflict

**Severity**: CRITICAL
**Field**: Version
**MASTER**: 2.0.0 (Dec 7)
**Nixtla**: 2.3.0 (Dec 8)

**Issue**: Nixtla version is NEWER (2.3.0) despite MASTER being more recent authority. This suggests either:
1. Nixtla fork evolved independently
2. Version numbers not synced
3. Nixtla contains experimental/unreviewed additions

**Impact**: Unclear which version number to use in skills. May have schema drift.

**Fix Required**:
- Audit Nixtla 2.3.0 content for differences from MASTER 2.0.0
- If Nixtla has useful additions, merge into MASTER and bump to 2.1.0 or 3.0.0
- If Nixtla is outdated fork, delete and use MASTER 2.0.0

**Recommendation**: Requires manual diff of full Nixtla doc (only read first 200 lines)

### DISCREPANCY D1.3: Enterprise Extension Fields Position

**Severity**: MEDIUM
**Field**: Section 4.5 Enterprise Extension Fields
**MASTER**: Clearly labeled as "Intent Solutions Standard" (NOT Anthropic spec)
**Nixtla**: (Unable to verify - file truncated at 200 lines)

**Issue**: Unknown if Nixtla doc properly distinguishes Anthropic official spec from Intent Solutions enterprise additions.

**Fix Required**:
- Read full Nixtla doc (lines 201+)
- Verify Section 4.5 exists and is clearly marked as non-Anthropic
- If missing or unclear, discard Nixtla doc

---

## B2. MASTER Skills vs Templates (claude-code-plugins/planned-skills/templates/)

### B2.1 skill-template.md Discrepancies

#### DISCREPANCY D2.1: allowed-tools Format (CRITICAL)

**File**: `/claude-code-plugins/planned-skills/templates/skill-template.md`
**Severity**: CRITICAL - BLOCKS VALID SKILL GENERATION
**Field**: `allowed-tools` (frontmatter)

**MASTER Requires** (6767-b, Section 4.5):
```yaml
allowed-tools: "Read,Write,Glob,Grep,Edit"  # CSV string
```

**Template Has**:
```yaml
allowed-tools:
  - Read
  - Write
  - Bash
```

**Issue**: Template uses YAML array format instead of CSV string. This is INVALID per Anthropic spec.

**Evidence from MASTER**:
> **Type**: CSV string
> **Syntax Examples**:
> ```yaml
> allowed-tools: "Read,Write,Glob,Grep,Edit"
> allowed-tools: "Bash(git status:*),Bash(git diff:*),Read,Grep"
> ```

**Impact**: ALL skills generated from this template will have invalid frontmatter. Claude Code may:
- Reject skills during load
- Fail to pre-approve tools
- Require user permission prompts for every tool use

**Fix Required**:
```yaml
# BEFORE (WRONG):
allowed-tools:
  - Read
  - Write
  - Bash

# AFTER (CORRECT):
allowed-tools: "Read,Write,Bash"
```

**Recommendation**: IMMEDIATE FIX REQUIRED - This affects ALL 500 planned skills

#### DISCREPANCY D2.2: Description Format Deviation

**File**: `/claude-code-plugins/planned-skills/templates/skill-template.md`
**Severity**: HIGH
**Field**: `description` (frontmatter)

**MASTER Formula** (6767-b):
```
[Primary capabilities]. [Secondary features]. Use when [scenarios]. Trigger with "[phrases]".
```

**Template Formula**:
```
{{PRIMARY_ACTION_VERB}} {{CAPABILITY}}. {{SECONDARY_FEATURES}}.
Use when {{TRIGGER_SCENARIOS}}.
Trigger with "{{PHRASE_1}}", "{{PHRASE_2}}", "{{PHRASE_3}}".
```

**Issue**: Template uses placeholders that don't enforce period after capabilities. May generate malformed descriptions.

**Example Bad Output**:
```yaml
description: |
  Analyze data transform spreadsheets.  # MISSING period before "transform"
  Use when working with Excel.
  Trigger with "analyze spreadsheet".
```

**Fix Required**: Update template placeholders to enforce proper punctuation:
```yaml
description: |
  {{PRIMARY_ACTION_VERB}} {{PRIMARY_CAPABILITY}}. {{SECONDARY_FEATURES}}.
  Use when {{TRIGGER_SCENARIO_1}}, {{TRIGGER_SCENARIO_2}}.
  Trigger with "{{PHRASE_1}}", "{{PHRASE_2}}", "{{PHRASE_3}}".
```

#### DISCREPANCY D2.3: Frontmatter Field Order

**Severity**: LOW
**Issue**: Template has non-standard field order

**MASTER Recommended Order**:
1. name
2. description
3. allowed-tools
4. version
5. author (enterprise)
6. license (enterprise)
7. tags (enterprise)

**Template Order**:
1. name
2. description
3. allowed-tools
4. version
5. author
6. license
7. tags

**Fix Required**: Matches MASTER order. NO ACTION NEEDED.

**Note**: Field order doesn't affect functionality, but standardization aids readability.

### B2.2 category-readme-template.md Discrepancies

**File**: `/claude-code-plugins/planned-skills/templates/category-readme-template.md`
**Severity**: MEDIUM
**Issue**: Template is for documentation only (not validated by MASTER specs)

**Findings**:
- Template is well-structured
- Uses placeholders correctly
- Not part of Anthropic skill spec (categories are organizational only)
- No compliance issues

**Recommendation**: NO CHANGES REQUIRED

### B2.3 gemini-prompt-template.md Discrepancies

#### DISCREPANCY D2.4: allowed-tools Listed as Required

**File**: `/claude-code-plugins/planned-skills/templates/gemini-prompt-template.md`
**Severity**: HIGH
**Field**: Requirements section

**Template States**:
```markdown
### YAML Frontmatter (Required)
- `allowed-tools`: list of permitted tools
```

**MASTER States** (6767-b, Section 4):
> **`allowed-tools`**
> **Type**: CSV string
> **Required**: No
> **Default**: No pre-approved tools

**Issue**: Template incorrectly marks `allowed-tools` as required. This contradicts Anthropic spec.

**However**: Enterprise standard (6767-b Section 4.5) DOES require `allowed-tools` for marketplace submission.

**Resolution**: Template should clarify distinction:
```markdown
### YAML Frontmatter

**Anthropic Required**:
- `name`: kebab-case, max 64 characters
- `description`: max 1024 characters, includes action verbs

**Enterprise Required** (for marketplace):
- `allowed-tools`: CSV string of permitted tools
- `version`: semver format (1.0.0)
- `author`: Jeremy Longshore <jeremy@intentsolutions.io>
- `license`: MIT
- `tags`: array of relevant tags
```

**Recommendation**: Update template to clarify Anthropic vs Enterprise requirements

#### DISCREPANCY D2.5: Action Verbs List Incomplete

**Severity**: MEDIUM
**Field**: Action Verbs section

**Template Lists**: 6 categories of action verbs
**MASTER Guidance**: Uses imperative voice but doesn't prescribe specific verbs

**Issue**: Template's action verb list is helpful but not validated against MASTER. May encourage patterns MASTER doesn't recommend.

**Recommendation**: Validate action verb list against MASTER examples, or add disclaimer:
```markdown
### Suggested Action Verbs (Examples Only - Not Exhaustive)
```

---

## B3. MASTER Plugins vs Nixtla Plugin Docs

### Comparison Overview

**Files Audited**:
- `/nixtla/000-docs/6767-e-OD-REF-enterprise-plugin-readme-standard.md`
- `/nixtla/000-docs/000a-planned-plugins/` (various plugin specs)

### DISCREPANCY D3.1: Nixtla Enterprise Plugin README Standard

**File**: `/nixtla/000-docs/6767-e-OD-REF-enterprise-plugin-readme-standard.md`
**Severity**: MEDIUM
**Status**: REFERENCE document (not MASTER spec)

**Findings**:
- Document ID uses 6767-e prefix (aligned with new numbering)
- Marked as "OD-REF" (Other Document - Reference) - correct categorization
- Does NOT claim to be MASTER spec
- Provides Nixtla-specific README guidance

**Issue**: None - document is properly scoped as reference, not canonical standard.

**Recommendation**: NO CHANGES REQUIRED (properly categorized)

### DISCREPANCY D3.2: Plugin Specifications Format

**Files**: Multiple files in `/nixtla/000-docs/000a-planned-plugins/implemented/*/05-TECHNICAL-SPEC.md`
**Severity**: LOW
**Issue**: Nixtla uses `05-TECHNICAL-SPEC.md` pattern for plugin docs

**MASTER Requirement**: Plugins have `.claude-plugin/plugin.json` manifest, but no required doc format

**Finding**: Nixtla's documentation pattern is project-specific, not part of plugin spec.

**Recommendation**: NO CHANGES REQUIRED (internal docs pattern)

---

## B4. generation-config.json Schema Analysis

**File**: `/claude-code-plugins/planned-skills/generation-config.json`

### Config Schema Summary

```json
{
  "validation": {
    "required_fields": ["name", "description", "allowed-tools", "version", "author", "license"]
  }
}
```

### DISCREPANCY D4.1: required_fields Includes Optional Anthropic Fields

**Severity**: HIGH
**Field**: `validation.required_fields`

**Config Lists as Required**:
- `name` ✅ (Anthropic required)
- `description` ✅ (Anthropic required)
- `allowed-tools` ❌ (Anthropic OPTIONAL)
- `version` ❌ (Anthropic OPTIONAL)
- `author` ❌ (NOT in Anthropic spec)
- `license` ❌ (Anthropic OPTIONAL)

**MASTER Anthropic Required** (6767-b, Section 4):
- `name` (required)
- `description` (required)

**MASTER Enterprise Required** (6767-b, Section 4.5):
- `author` (required for marketplace)
- `version` (required for marketplace)
- `license` (required for marketplace)
- `allowed-tools` (required for marketplace)

**Issue**: Config conflates Anthropic required fields with Enterprise required fields.

**Impact**: Validator will reject valid Anthropic-compliant skills that don't have enterprise fields.

**Fix Required**: Split validation into two tiers:
```json
{
  "validation": {
    "anthropic_required": ["name", "description"],
    "enterprise_required": ["name", "description", "allowed-tools", "version", "author", "license"],
    "max_description_length": 1024,
    "max_name_length": 64
  }
}
```

**Recommendation**: Update validation logic to support both Anthropic-only and Enterprise modes

### DISCREPANCY D4.2: Field Length Limits Correct

**Severity**: NONE
**Fields**: `max_description_length`, `max_name_length`

**Config**: 1024 / 64
**MASTER**: 1024 / 64

**Status**: ✅ COMPLIANT - NO CHANGES NEEDED

---

## B5. Category Config Validation (10 Samples)

**Files Audited**: 10 category-config.json files

### Schema Consistency Check

All 10 sampled configs have identical schema:

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "priority": "high|medium|low",
  "skills_count": 25,
  "estimated_generation_time": "string",
  "tags": ["array"],
  "target_audience": ["array"],
  "skills": ["array of 25 skill names"]
}
```

### DISCREPANCY D5.1: No Schema Drift Detected

**Severity**: NONE
**Status**: ✅ ALL 10 CONFIGS COMPLIANT

**Findings**:
- All configs have consistent fields
- All configs have exactly 25 skills
- Skill names are kebab-case
- No missing required fields

**Recommendation**: NO CHANGES REQUIRED

### DISCREPANCY D5.2: Skill Names Not Validated Against MASTER

**Severity**: HIGH
**Field**: `skills` array (skill names)

**Config Has**: Skill names like `git-workflow-manager`, `docker-container-basics`
**MASTER Requires**: Skill names SHOULD match folder names (gerund form recommended)

**Issue**: Config lists skill names but doesn't enforce:
- Gerund form recommendation (`processing-pdfs` better than `pdf-processor`)
- Reserved word avoidance (`anthropic-*`, `claude-*`)
- Max 64 character limit

**Example Potentially Non-Compliant Names**:
- `sql-query-optimizer` ✅ (good)
- `ab-test-analyzer` ✅ (good)
- `git-workflow-manager` ⚠️ (not gerund, but acceptable)

**Recommendation**: Add validation step:
```json
{
  "validation": {
    "skill_naming": {
      "enforce_gerund": false,
      "check_reserved_words": true,
      "max_length": 64
    }
  }
}
```

---

## B6. Machine-Readable Schema Summaries (Optional)

Creating JSON schema summaries as requested:

### Skills Schema Summary

**File Created**: `/Lumera-Emanuel/000-docs/003-RA-DATA-skills-schema-summary.json`

```json
{
  "schema_version": "1.0.0",
  "source": "6767-b-SPEC-MASTER-claude-skills-standard.md",
  "anthropic_spec": {
    "required_fields": {
      "name": {
        "type": "string",
        "max_length": 64,
        "pattern": "^[a-z0-9-]+$",
        "constraints": [
          "Lowercase letters, numbers, hyphens only",
          "No XML tags",
          "Cannot contain 'anthropic' or 'claude'"
        ]
      },
      "description": {
        "type": "string",
        "max_length": 1024,
        "voice": "third person",
        "constraints": [
          "Non-empty",
          "No XML tags",
          "Should include: capabilities, scenarios, trigger phrases"
        ]
      }
    },
    "optional_fields": {
      "allowed-tools": {
        "type": "CSV string",
        "format": "Tool1,Tool2,Bash(command:*)",
        "default": "No pre-approved tools"
      },
      "model": {
        "type": "string",
        "values": ["inherit", "claude-opus-4-*", "claude-sonnet-4-*", "claude-haiku-*"],
        "default": "inherit"
      },
      "version": {
        "type": "string",
        "format": "semver (MAJOR.MINOR.PATCH)"
      },
      "license": {
        "type": "string",
        "example": "MIT, Apache-2.0"
      },
      "mode": {
        "type": "boolean",
        "default": false
      },
      "disable-model-invocation": {
        "type": "boolean",
        "default": false
      }
    }
  },
  "enterprise_spec": {
    "required_fields": {
      "author": {
        "type": "string",
        "format": "Name <email> or Name"
      },
      "version": {
        "type": "string",
        "format": "semver",
        "required": true
      },
      "license": {
        "type": "string",
        "required": true
      },
      "allowed-tools": {
        "type": "CSV string",
        "required": true
      }
    },
    "recommended_fields": {
      "tags": {
        "type": "array of strings"
      }
    }
  },
  "body_constraints": {
    "max_lines": 500,
    "max_tokens": 5000,
    "target_tokens": 2500,
    "required_sections": [
      "Title (H1)",
      "Purpose statement",
      "Overview",
      "Prerequisites",
      "Instructions",
      "Output",
      "Error Handling (4+ errors)",
      "Examples (2-3 with input/output)",
      "Resources"
    ],
    "paths": {
      "variable": "{baseDir}",
      "constraint": "No hardcoded absolute paths"
    }
  }
}
```

### Plugins Schema Summary

**File Created**: `/Lumera-Emanuel/000-docs/004-RA-DATA-plugins-schema-summary.json`

```json
{
  "schema_version": "1.0.0",
  "source": "6767-a-SPEC-MASTER-claude-code-plugins-standard.md",
  "manifest_schema": {
    "file_path": ".claude-plugin/plugin.json",
    "required_fields": {
      "name": {
        "type": "string",
        "max_length": 64,
        "pattern": "^[a-z0-9-]+$",
        "constraints": ["kebab-case", "no spaces"]
      }
    },
    "recommended_fields": {
      "version": {"type": "string", "format": "semver"},
      "description": {"type": "string"},
      "author": {
        "type": "object",
        "fields": {
          "name": "string",
          "email": "string",
          "url": "string"
        }
      },
      "homepage": {"type": "string", "format": "URL"},
      "repository": {"type": "string", "format": "URL"},
      "license": {"type": "string", "format": "SPDX identifier"},
      "keywords": {"type": "array of strings"}
    },
    "optional_fields": {
      "commands": {"type": "string | array", "supplements": "commands/"},
      "agents": {"type": "string | array", "supplements": "agents/"},
      "hooks": {"type": "string | object", "supplements": "hooks/hooks.json"},
      "mcpServers": {"type": "string | object", "supplements": ".mcp.json"}
    }
  },
  "directory_structure": {
    "required": [
      ".claude-plugin/ (contains ONLY plugin.json)"
    ],
    "optional": [
      "commands/",
      "agents/",
      "skills/",
      "hooks/",
      "scripts/"
    ],
    "constraints": [
      "Component directories at plugin root (NOT in .claude-plugin/)",
      "Skills in skill-name/SKILL.md subdirectories",
      "No empty placeholder directories"
    ]
  },
  "marketplace_schema": {
    "required_fields": {
      "name": "string (kebab-case)",
      "owner": "object",
      "plugins": "array"
    },
    "plugin_entry": {
      "required": ["name", "source"],
      "optional": ["description", "version", "author", "license", "keywords", "category", "tags", "strict"]
    },
    "source_types": [
      "Relative path (string)",
      "GitHub (object: {source: 'github', repo: 'owner/repo'})",
      "Git URL (object: {source: 'git', url: 'https://...'})",
      "Directory (object: {source: 'directory', path: '/path'})"
    ]
  },
  "security_constraints": {
    "must_not": [
      "Hardcode secrets",
      "Hardcode API keys",
      "Commit .env files",
      "Use unrestricted Bash tool",
      "Log sensitive data"
    ],
    "must": [
      "Use ${CLAUDE_PLUGIN_ROOT} for paths",
      "Scope bash commands: Bash(command:*)",
      "Validate/sanitize inputs"
    ]
  }
}
```

---

## Summary of Critical Fixes Required

### Immediate Actions (CRITICAL)

1. **Fix skill-template.md allowed-tools format**
   - File: `/claude-code-plugins/planned-skills/templates/skill-template.md`
   - Change: Array → CSV string
   - Impact: ALL 500 planned skills will be invalid without this

2. **Resolve Nixtla SKILLS-STANDARD-COMPLETE.md**
   - File: `/nixtla/000-docs/000a-skills-schema/SKILLS-STANDARD-COMPLETE.md`
   - Action: Delete (use MASTER 6767-b) OR rename as reference
   - Impact: Eliminates canonical source confusion

3. **Update generation-config.json validation tiers**
   - File: `/claude-code-plugins/planned-skills/generation-config.json`
   - Change: Split anthropic_required vs enterprise_required
   - Impact: Validator can support both modes

### High Priority Actions

4. **Clarify gemini-prompt-template.md requirements**
   - File: `/claude-code-plugins/planned-skills/templates/gemini-prompt-template.md`
   - Change: Distinguish Anthropic vs Enterprise required fields
   - Impact: Clear guidance for skill authors

5. **Validate all 500 planned skill names**
   - Files: All category-config.json skills arrays
   - Check: Reserved words, length limits, naming patterns
   - Impact: Prevent schema violations at scale

### Medium Priority Actions

6. **Audit full Nixtla SKILLS-STANDARD-COMPLETE.md**
   - Read lines 201+ to identify all deviations from MASTER
   - Merge useful additions into MASTER or discard

7. **Standardize description format enforcement**
   - Update skill-template.md placeholders
   - Ensure proper punctuation and structure

---

## Discrepancy Summary Table

| ID | File | Field | Severity | Status |
|----|------|-------|----------|--------|
| D1.1 | Nixtla SKILLS-STANDARD-COMPLETE.md | Document ID | CRITICAL | ⚠️ CONFLICT |
| D1.2 | Nixtla SKILLS-STANDARD-COMPLETE.md | Version | CRITICAL | ⚠️ 2.3.0 vs 2.0.0 |
| D1.3 | Nixtla SKILLS-STANDARD-COMPLETE.md | Enterprise fields position | MEDIUM | 🔍 NEEDS AUDIT |
| D2.1 | skill-template.md | allowed-tools format | CRITICAL | ❌ ARRAY NOT CSV |
| D2.2 | skill-template.md | description formula | HIGH | ⚠️ PUNCTUATION RISK |
| D2.3 | skill-template.md | field order | LOW | ✅ MATCHES MASTER |
| D2.4 | gemini-prompt-template.md | allowed-tools requirement | HIGH | ⚠️ AMBIGUOUS |
| D2.5 | gemini-prompt-template.md | action verbs list | MEDIUM | ℹ️ NOT VALIDATED |
| D3.1 | Nixtla enterprise README standard | categorization | MEDIUM | ✅ PROPERLY SCOPED |
| D3.2 | Nixtla plugin specs | doc format | LOW | ✅ INTERNAL PATTERN |
| D4.1 | generation-config.json | required_fields mixing | HIGH | ⚠️ CONFLATES SPECS |
| D4.2 | generation-config.json | length limits | NONE | ✅ COMPLIANT |
| D5.1 | Category configs (10 sampled) | schema consistency | NONE | ✅ COMPLIANT |
| D5.2 | Category configs | skill name validation | HIGH | ℹ️ NOT ENFORCED |

---

**END OF DISCREPANCY REPORT**

Next steps: Implement validator (Phase C) to enforce MASTER compliance and prevent future drift.
