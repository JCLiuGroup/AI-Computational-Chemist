---
name: rsess
description: Run commands on a REMOTE server through a persistent shell that survives disconnects, by driving a tmux session that lives ON THE REMOTE. Use when you need shell state (cwd, env vars, activated venvs, a running REPL/daemon) to persist across multiple commands on an SSH-reachable host — instead of `ssh host cmd`, which starts a fresh shell every time and loses all state. Do NOT use rsess when the agent is already running on the target machine — run commands directly with the native shell.
---

# rsess

Use `rsess` only to drive a remote tmux-backed shell whose state must persist across
SSH calls and disconnects. If the agent already runs on the target, use the native
shell instead.

## Required inputs

- An SSH-reachable host (`Host` alias from `~/.ssh/config`, or `user@host`).
- tmux on the remote, or user approval to upload the bundled static binary (`scripts/tmux`, linux x86-64 musl).

## Route map

| Need | Load or run |
|---|---|
| command syntax, sessions, transfer, defaults, and tmux upload | `references/running.md`; `scripts/rsess` |
| first-use and per-session preflight | `references/validation.md` |
| connection, tmux, timeout, output, or quota failures | `references/errors.md` |
| tmux/SSH/static-build documentation | `references/resources.md` |

## Workflow

1. Confirm the explicit remote target, then run the probe and validation in
   `references/validation.md`.
2. Open one topic session and retain the exact printed session name.
3. Use `run` for commands, `peek` for the live pane, and the configured scp/rsync route
   for files. Revalidate before HPC submission.
4. Close the session deliberately; use recovery guidance rather than recreating a
   session blindly.

## Hard guardrails

- Never use `rsess` when already on the target or with an unconfirmed SSH target.
- Do not `run` `exit`, or `set -e` followed by a possibly failing line; close sessions
  with `rsess close`.
- Read `run` output from its return value. `peek` shows the pane, not the per-command
  capture.
- Never put secrets in commands or use the tmux pane for file transfer; commands are
  logged remotely.
- Confirm destructive remote actions and obtain explicit approval before uploading the
  bundled tmux binary or installing anything.
