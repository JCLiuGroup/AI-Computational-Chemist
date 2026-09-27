# AICC CLI Contract

- `aicc status`, `aicc task show`, `aicc task ready`, and `aicc job status` are
  read-only.
- Task and Job mutations reuse the canonical scripts under
  `procedures/research-orchestrator/scripts/`; command modules remain thin adapters.
- Job submission requires a matching active Lease. An active or ambiguous attempt in
  the same work directory blocks another submission.
- Operator recovery requires an explicit reason and confirmation and is appended to
  `.research/events.jsonl`.
- Skill commands modify only AICC-owned instruction blocks and symlinks. Foreign files,
  symlinks, and Skill configuration entries are preserved or reported as conflicts.
- `aicc skill disable --stale` is the explicit recovery exception: after `--confirm`,
  it may remove a same-name skill or instruction symlink whose target is missing, or
  a link whose live target validates as a retired AICC collection. It does not
  remove current-source links or live foreign links, and each candidate is
  revalidated again at the removal boundary.
- Global Skill scope targets Codex paths; local scope targets the current directory.
- `aicc skill migrate` is the only Skill command that edits legacy Codex
  `config.toml`; it creates a backup before changing confirmed AICC entries.
