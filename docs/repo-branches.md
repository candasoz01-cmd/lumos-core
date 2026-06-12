# Repository branch strategy

Canonical reference for active branches in `lumos-core`. Product work targets **`main`** unless a task explicitly names another branch.

## Default / active branch

| Setting | Value |
|---------|-------|
| Canonical default branch | `main` |
| GitHub default branch | `main` |
| `origin/HEAD` | `origin/main` |

Local clones should track `main` for day-to-day development, releases, and CI expectations.

## Remote branches (non-default)

### `kando/main`

- **Not** the default branch.
- Archived line from an older embedded-structure layout.
- Kept on the remote for history and comparison; **not** deleted.
- **Do not** perform a full merge of `kando/main` into `main`.
- If material is needed from that line, use a separate, scoped analysis (cherry-pick, diff review, or dedicated doc) — not a blanket merge.

### `feature/generic-cache-layer` (retired)

- **Deleted** from the remote; no longer an active or preserved review branch.
- Useful `cursor_bridge` hunks from that line were ported to **`main`** via [PR #152](https://github.com/candasoz01-cmd/lumos-core/pull/152).
- Do not recreate or track this branch; refer to `main` for the merged material.

## Unrelated histories

`kando/main` and `main` may share **unrelated histories** (different root commits or divergent early structure). A naive `git merge kando/main` into `main` can fail or produce misleading history. Prefer explicit diff and targeted porting over merge-by-default.

## Summary

- Work on **`main`**; GitHub and `origin/HEAD` point there.
- **`kando/main`**: legacy archive — preserve on remote, no full merge into `main`.
- **`feature/generic-cache-layer`**: retired — deleted from remote; relevant `cursor_bridge` work is on **`main`** (PR #152).
