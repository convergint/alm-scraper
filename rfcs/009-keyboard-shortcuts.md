# RFC: Keyboard Shortcuts for Web UI

**Status:** Accepted  
**Author:** Claude  
**Created:** 2026-02-01

---

## Summary

Add keyboard shortcuts to the ALM web UI for power users who want faster navigation. Primary use case: quickly jumping to a specific defect by ID without reaching for the mouse.

## Problem

Currently, to view a specific defect:

1. Click in search box
2. Type the defect ID
3. Wait for results
4. Click on the result

For users who know the defect ID they want, this is slow. They want something like vim-style commands: type a sequence, enter an ID, and go directly there.

## Proposed Solution

Add a keyboard shortcut system inspired by vim/gmail conventions. When not focused on an input, key sequences trigger actions.

### User Experience

**Go to defect:**

```
g d 993 <Enter>  →  navigates to /defects/993
```

**Other potential shortcuts:**

```
/            →  focus search box
g h          →  go home (defect list)
g s          →  go to stats/dashboard
?            →  show keyboard shortcut help
Escape       →  clear focus / close dialogs
j / k        →  move selection down/up in list (future)
```

### Visual Feedback

When a chord sequence starts (e.g., user presses `g`), show a subtle indicator:

```
┌─────────────────────┐
│ g ...               │  ← bottom-left toast, disappears after 1s or on completion
└─────────────────────┘
```

For `g d`, prompt for ID:

```
┌─────────────────────┐
│ Go to defect: 993_  │  ← inline input, Enter to confirm, Escape to cancel
└─────────────────────┘
```

## Decisions

1. **Key sequence style** - Vim-style chords: `g d 993 <Enter>` (two keys, then input, then confirm)

2. **Discoverability** - Both `?` help overlay AND footer hint "Press ? for keyboard shortcuts"

3. **Scope** - Vim-style navigation (j/k/enter), search focus (`/`), and go-to-defect (`g d`)

4. **Conflict handling** - Only activate shortcuts when no input is focused

5. **ID validation** - Validate first, show error in toast if defect doesn't exist

## Alternatives Considered

| Option                  | Pros                                      | Cons                                          |
| ----------------------- | ----------------------------------------- | --------------------------------------------- |
| Command palette (Cmd+K) | Familiar from VS Code/Slack, discoverable | More complex to implement, needs fuzzy search |
| Vim-style (g d 993)     | Fast for power users, no modifier keys    | Learning curve, not obvious                   |
| URL bar only            | Already works (/defects/993)              | Requires knowing URL structure                |
| Quick search box        | Simple, always visible                    | Takes up UI space                             |

## Future Enhancements

1. **List navigation** - j/k to move through defect list, Enter to open
2. **Bulk selection** - x to toggle select, then bulk actions
3. **Quick filters** - `f p 1` to filter to P1, `f s b` for blocked status
4. **Recent defects** - `g r` to show recently viewed
5. **Customizable shortcuts** - Let users remap keys

## References

- [Gmail keyboard shortcuts](https://support.google.com/mail/answer/6594)
- [GitHub keyboard shortcuts](https://docs.github.com/en/get-started/accessibility/keyboard-shortcuts)
- [Vim-style navigation in web apps](https://vimium.github.io/)
