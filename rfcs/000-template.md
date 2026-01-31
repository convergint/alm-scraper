# RFC: [Feature Name]

**Status:** Draft | Accepted | Implemented  
**Author:** [Name]  
**Created:** YYYY-MM-DD

## Pre-Submission Checklist

Before submitting this RFC, verify the items that apply:

- [ ] **Error messages are actionable** - Every error tells the user what to do next
- [ ] **Examples show real output** - Including error cases and edge cases
- [ ] **Failure modes are documented** - What happens when things go wrong?
- [ ] **Data safety is addressed** - No operation can lose good data
- [ ] **Cancellation is graceful** - Ctrl+C leaves system in clean state
- [ ] **No surprises** - Behavior is predictable and documented

**Note:** Delete sections that don't apply to your RFC. Not every RFC needs every section - trim ruthlessly. A focused RFC is easier to review and implement.

---

## Summary

One paragraph. What is this? Why does it matter?

## Problem

What's broken or missing today? Include:

- Concrete examples of current pain
- User quotes or scenarios if applicable
- Why this matters for the user experience

## Proposed Solution

High-level approach. What does success look like?

### User Experience

Show the complete user journey, including what they see in the terminal.

**Before:**

```bash
# What users do today (the pain)
$ alm show 993
Error: no local data found, run 'alm sync' first
```

**After:**

```bash
# What they'll do with this feature
$ alm show 993
Defect #993: Login timeout on SSO redirect
Status: Open | Priority: P2-High | Owner: jsmith
Created: 2025-01-15 | Modified: 2025-01-28

Description:
  Users experience 30s timeout when SSO redirect takes too long...
```

### Commands / API

Show the complete interface. For CLI tools:

- Full command syntax with all options
- Example output (including status messages)
- Help text users will see

```bash
$ alm new-command --help
Usage: alm new-command [OPTIONS] ARGUMENT

  Description of what this command does.

Options:
  --flag        Description of flag
  --option VAL  Description of option
  --help        Show this message and exit.
```

## Error Handling

For each error condition, document what the user sees and how they recover.

| Scenario         | What User Sees                                   | Recovery Action     |
| ---------------- | ------------------------------------------------ | ------------------- |
| No local data    | `Error: No defects synced. Run 'alm sync' first` | Run sync command    |
| Defect not found | `Error: Defect #9999 not found`                  | Check the defect ID |
| Auth expired     | `Error: ALM session expired. Re-authenticate.`   | Re-run auth flow    |

### Example Error Messages

Show complete error output as users will see it:

```bash
$ alm show 9999
Error: Defect #9999 not found

No defect with ID 9999 exists in local data.
Last synced: 2025-01-28 14:32:00 (847 defects)

Try:
  alm sync        # refresh from ALM
  alm list        # see available defects
```

## Safety & Edge Cases

Address the relevant items below. Delete subsections that don't apply.

### 1. Failure Mid-Operation

What happens if the operation fails halfway through?

- **Risk:** [Describe the risk]
- **Mitigation:** [How we handle it - e.g., atomic operations, temp files, transactions]

### 2. Data Loss Prevention

Can this operation lose or corrupt user data?

- **Risk:** [Describe the risk]
- **Mitigation:** [How we prevent data loss]

### 3. Cancellation (Ctrl+C)

What happens if the user cancels mid-operation?

- **Behavior:** [What happens - clean shutdown, partial state, etc.]
- **Cleanup:** [Any cleanup performed]

### 4. Invalid/Partial Input

What happens with malformed or incomplete input?

- **Validation:** [When and how we validate]
- **Error:** [What error message the user sees]

### 5. Network/External Failures

What happens when external dependencies fail?

- **Timeouts:** [How we handle timeouts]
- **Retries:** [Retry policy, if any]
- **Fallback:** [Any fallback behavior]

## Implementation Details

Technical approach. Focus on the interesting parts, not boilerplate.

### File Structure

```
src/alm_scraper/
├── new_module/
│   ├── __init__.py
│   └── core.py      # Main implementation
└── cli.py           # CLI integration
```

### Key Components

```python
# Core logic (pseudocode or actual code)
def key_function(input: str) -> Result:
    """Brief description of what this does."""
    # Implementation notes
    ...
```

### Configuration

Any new configuration values? Prefer environment variables for testability:

```python
# Good: Environment variable with sensible default
def get_data_dir() -> Path:
    if env_dir := os.environ.get("ALM_DATA_DIR"):
        return Path(env_dir)
    return Path.home() / ".local" / "share" / "alm-scraper" / "data"

# Bad: Module-level constant that requires monkeypatching to test
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "alm-scraper" / "data"
```

### Dependencies

Any new dependencies required? Add to `pyproject.toml`:

```toml
dependencies = [
    "new-package>=1.0.0",  # Why we need this
]
```

## Testing Strategy

How will this be tested? Include relevant subsections.

### Unit Tests

What pure logic can be tested in isolation?

```python
def test_key_function_handles_edge_case():
    """Test description."""
    result = key_function("edge case input")
    assert result == expected
```

### Integration Tests

What end-to-end scenarios need verification?

```python
def test_command_produces_correct_output():
    """Test the full command execution."""
    result = runner.invoke(main, ["command", "arg"])
    assert result.exit_code == 0
    assert "expected output" in result.stdout
```

### Manual Testing Checklist

- [ ] Happy path works as documented
- [ ] Error messages appear correctly
- [ ] Ctrl+C cancellation is clean

## Migration / Compatibility

### Breaking Changes

Is this a breaking change? If yes:

- What breaks?
- Who is affected?
- How do they migrate?

### Deprecation Path

If deprecating existing behavior:

```bash
# Old way (deprecated, shows warning)
$ alm old-command
Warning: 'old-command' is deprecated. Use 'new-command' instead.

# New way
$ alm new-command
```

### Backward Compatibility

What existing behavior is preserved?

## Alternatives Considered

| Option          | Pros             | Cons                  | Why Not                   |
| --------------- | ---------------- | --------------------- | ------------------------- |
| [Status quo]    | No work required | [Current pain points] | Doesn't solve the problem |
| [Alternative A] | [Benefits]       | [Drawbacks]           | [Reason for rejection]    |
| [Alternative B] | [Benefits]       | [Drawbacks]           | [Reason for rejection]    |

## Open Questions

Questions that need answers before implementation:

1. **[Question 1]** - Context for why this matters
2. **[Question 2]** - Context for why this matters

## Decisions

Record decisions made during review. Update this section as questions are resolved.

1. **[Question]:** [Answer and rationale]
2. **[Question]:** [Answer and rationale]

## Out of Scope

Explicitly list what this RFC does _not_ cover:

| Item             | Rationale                   |
| ---------------- | --------------------------- |
| [Feature X]      | Could be a follow-up RFC    |
| [Platform Y]     | Not enough users to justify |
| [Optimization Z] | Premature; measure first    |

## Future Enhancements

Ideas that could build on this work later (but are not part of this RFC):

1. **[Enhancement 1]** - Brief description
2. **[Enhancement 2]** - Brief description

## References

- [Link to relevant documentation]
- [Link to prior art or inspiration]
- [Link to related RFCs]
