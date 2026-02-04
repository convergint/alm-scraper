# RFC: Support Paste in Go-to-Defect Prompt

**Status:** Implemented  
**Author:** Brian  
**Created:** 2026-02-04

## Summary

Enable pasting defect IDs into the "go to defect" prompt (`g d`). Currently the prompt only accepts individual keypresses, so users can't paste an ID copied from an email or chat.

## Problem

Common workflow:

1. Receive email: "Please look at defect 12345"
2. Copy "12345" from email
3. Open alm-scraper UI, press `g d`
4. Try to paste... nothing happens
5. Manually type "12345" digit by digit

The current implementation captures individual `keydown` events and builds up the ID string one character at a time. It doesn't handle the `paste` event, which is how clipboard data arrives.

## Proposed Solution

Replace the custom keypress-based input with an actual `<input>` element that natively supports paste, selection, and standard text editing.

### User Experience

**Before:**

```
Go to defect: 123_     (can only type digits one at a time)
```

**After:**

```
Go to defect: [12345    ]     (real input, paste works, can select/delete)
```

The prompt should:

- Auto-focus when opened
- Accept pasted content (filtering to digits only)
- Support standard editing (Ctrl+A, backspace, delete, arrow keys)
- Submit on Enter, cancel on Escape
- Look visually similar to current prompt

## Implementation Details

### Option A: Real `<input>` element

Replace the span-based display with an actual input:

```svelte
{#if showGoToDefect}
  <div class="fixed bottom-16 left-4 bg-background border rounded px-3 py-2 shadow-lg z-50 flex items-center gap-2">
    <label for="goto-defect-input" class="text-sm text-muted-foreground">Go to defect:</label>
    <input
      id="goto-defect-input"
      type="text"
      inputmode="numeric"
      pattern="[0-9]*"
      bind:value={goToDefectId}
      onkeydown={handleGoToDefectKeydown}
      onpaste={handleGoToDefectPaste}
      class="w-24 bg-transparent border-b border-primary font-mono text-primary focus:outline-none"
      autofocus
    />
    <span class="text-xs text-muted-foreground ml-2">Enter to go, Esc to cancel</span>
  </div>
{/if}
```

Key handler filters non-digits on paste:

```typescript
function handleGoToDefectPaste(e: ClipboardEvent) {
  e.preventDefault();
  const text = e.clipboardData?.getData("text") ?? "";
  const digits = text.replace(/\D/g, "");
  goToDefectId += digits;
}

function handleGoToDefectKeydown(e: KeyboardEvent) {
  if (e.key === "Enter") {
    if (goToDefectId) validateAndGoToDefect(goToDefectId);
    showGoToDefect = false;
    goToDefectId = "";
    e.preventDefault();
  } else if (e.key === "Escape") {
    showGoToDefect = false;
    goToDefectId = "";
    e.preventDefault();
  }
}
```

### Option B: Add paste handler to existing implementation

Keep the span-based display but add a paste event listener:

```typescript
function handlePaste(e: ClipboardEvent) {
  if (!showGoToDefect) return;
  const text = e.clipboardData?.getData("text") ?? "";
  const digits = text.replace(/\D/g, "");
  goToDefectId += digits;
  e.preventDefault();
}

onMount(() => {
  window.addEventListener("keydown", handleKeyDown);
  window.addEventListener("paste", handlePaste);
  return () => {
    window.removeEventListener("keydown", handleKeyDown);
    window.removeEventListener("paste", handlePaste);
  };
});
```

### Recommendation

**Option A** is preferred because:

- Uses native browser input behavior (selection, cursor positioning, undo)
- More accessible (screen readers understand inputs)
- Simpler to maintain - we're not reimplementing text input
- `inputmode="numeric"` shows number keyboard on mobile

Option B preserves the current visual style but reimplements text editing poorly.

## Testing Strategy

### Manual Testing Checklist

- [ ] `g d` opens prompt with input focused
- [ ] Typing digits works
- [ ] Pasting a plain number (e.g., "12345") works
- [ ] Pasting text with non-digits (e.g., "Defect #12345:") extracts just "12345"
- [ ] Backspace/delete work
- [ ] Enter navigates to defect
- [ ] Escape closes prompt
- [ ] Clicking outside closes prompt (if desired)
- [ ] Tab doesn't escape the prompt unexpectedly

## Out of Scope

| Item                        | Rationale                          |
| --------------------------- | ---------------------------------- |
| Autocomplete/suggestions    | Over-engineering for this use case |
| Defect title preview        | Nice-to-have, separate RFC         |
| History of recently visited | Separate feature                   |

## Open Questions

1. **Should clicking outside the prompt close it?** Currently only Escape closes it. An input element makes click-outside-to-close more natural.
   - Proposal: Yes, close on click outside for consistency with other modals
