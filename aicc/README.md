# AICC CLI

The CLI is an optional extension to the skill collection. It provides `status`, `task`,
`job`, `skill`, and `doctor` commands; run `aicc --help` and each command's `--help` for
the current interface.

`aicc.py` and `launcher.sh` provide routing and installation. Built-in commands live in
`commands/`, while research protocol logic remains in
`procedures/research-orchestrator/scripts/`. Keep the CLI thin: reuse canonical helpers,
avoid scientific logic in command modules, and cover changes in `tests/smoke_test.py`.
Behavioral and write-safety boundaries are recorded in [`CONTRACT.md`](CONTRACT.md).
