# RFC: Output Formats

**Status:** Accepted  
**Author:** Brian Brennan  
**Created:** 2025-01-31

---

## Summary

Add markdown (and potentially other) output formats to `alm show` for easy sharing and documentation.

## Problem

The current `alm show` output is great for terminal viewing, but sometimes you want to:

- Paste a defect into Slack/Teams
- Add it to a document or wiki
- Share with someone who doesn't have the CLI

## Proposed Solution

Add a `--format` flag to `alm show`:

```bash
# Default: rich terminal output
alm show 993

# Markdown output
alm show 993 --format=markdown
alm show 993 -f md

# JSON output (for scripting)
alm show 993 --format=json
alm show 993 -f json
```

### Markdown Format

```markdown
# Defect #993: Login timeout on SSO redirect

**Status:** Open | **Priority:** P2-High | **Owner:** jsmith

| Field       | Value      |
| ----------- | ---------- |
| Detected by | jsmith     |
| Created     | 2025-01-15 |
| Modified    | 2025-01-28 |
| Application | SSO        |
| Workstream  | Identity   |

## Description

Users experience 30s timeout when SSO redirect takes too long...

## Dev Comments

Investigating load balancer config...
```

### JSON Format

Just dump the Defect model as JSON - useful for piping to `jq` or other tools.

```bash
alm show 993 -f json | jq '.status'
```

## Open Questions

1. **Should markdown go to stdout?** - Currently `alm show` uses Rich which writes to stdout. Markdown should probably also go to stdout so you can `alm show 993 -f md | pbcopy`. Status messages stay on stderr.

## Decisions

(none yet)

## Out of Scope

- Bulk export (`alm export --format=markdown` for all defects) - separate RFC if needed
- HTML format - markdown covers this use case well enough
