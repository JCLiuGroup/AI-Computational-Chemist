#!/usr/bin/env sh
set -eu

usage() {
  cat <<'USAGE'
Usage: ./install.sh [options]

Install this computational-chemistry skill collection and its lightweight `aicc`
command for one or more agent harnesses. It does not install VASP, VASPKIT, OVITO,
Gaussian, GROMACS, LAMMPS, pseudopotentials, basis sets, or licensed data.

Both modes COPY the collection to a stable location, REWRITE every cross-reference
(knowledge/..., tools/..., procedures/...) inside the copy to an ABSOLUTE path, and
SYMLINK the skills into each harness's discovery directory. Absolute refs resolve on
every harness regardless of symlink-following or working directory -- at the cost of
movability: the copy must stay put (re-run install if you relocate it).

  OUTSIDE the repo, no --target  -> self-contained install in the CURRENT directory,
      wired for every harness in --harness (default: all). One canonical skill store
      (.agents/skills/) + one AGENTS.md, with thin per-harness aliases:
        codex / kimi / pi / opencode : .agents/skills/   + AGENTS.md
        qwen (Qwen Code)             : .qwen/skills/      + QWEN.md   (also reads .agents + AGENTS.md)
        claude (Claude Code)         : .claude/skills/    + CLAUDE.md
        zcode (ZCode)                : .zcode/skills/     + AGENTS.md (project path UNVERIFIED, see NOTE)
      collection copy -> ./.auto-computational-chemist/

  INSIDE the repo, or with --target  -> shared install into one skills dir:
      copy   -> <dir-of-target>/.auto-computational-chemist/  (refs rewritten absolute)
      skills -> the target dir (default $CODEX_HOME/skills, ~/.codex/skills, ~/.claude/skills)
      NOTE: no longer symlinks the live repo, so `git pull` does not auto-propagate;
      re-run install to update.

Absolute-path rewriting needs python3; without it the rewrite is skipped (with a
warning) and refs stay relative.

The `aicc` launcher selects from collections registered by this installer under
${XDG_STATE_HOME:-$HOME/.local/state}/aicc. Project registrations apply only while
the command runs inside that project; shared installs atomically set the default.
Set AICC_COLLECTION (or AICC_SOURCE) for an explicit override. An existing non-AICC
command at ~/.local/bin/aicc is never overwritten, including with --force.
An existing collection directory is never reused; pass --force to refresh it from
this checkout.

Options:
  --harness LIST     Comma-separated harnesses, or "all" (default outside the repo).
                     Known: claude, codex, zcode, kimi, qwen, pi, opencode, generic.
                     (claudecode = claude.)
  --target DIR       Skill directory to install into (forces shared mode).
  --mode link|copy   Place each skill by symlink (link, default) or copy (copy).
  --project DIR      Also install instruction file(s) (AGENTS.md / CLAUDE.md / QWEN.md
                     per --harness, from the rewritten copy) into DIR.
  --force            Refresh an existing collection copy / replace existing skills.
  --dry-run          Print actions without changing files.
  -h, --help         Show this help.

NOTE (zcode): ZCode's documented stable skills path is GLOBAL ~/.zcode/skills/ or its
in-app "import to Project"; the per-project .zcode/skills/ this writes is inferred and
unverified. Its workspace AGENTS.md is read normally.

Examples:
  cd /path/to/project && /path/to/install.sh                 # self-contained, all harnesses
  cd /path/to/project && /path/to/install.sh --harness claude,codex,qwen
  ./install.sh --target ~/.codex/skills                      # shared (codex global)
USAGE
}

script_dir() {
  cd "$(dirname "$0")" >/dev/null 2>&1
  pwd -P
}

die() {
  printf '%s\n' "install.sh: $*" >&2
  exit 1
}

ALL_HARNESSES="claude codex zcode kimi qwen pi opencode"

# Normalized, space-separated harness selection (expands "all", keeps claudecode->claude in has_harness).
harness_list() {
  case "$HARNESS" in
    all|"") printf '%s' "$ALL_HARNESSES" ;;
    *) printf '%s' "$HARNESS" | tr ',' ' ' ;;
  esac
}

has_harness() {
  for _h in $(harness_list); do
    [ "$_h" = "claudecode" ] && _h="claude"
    [ "$_h" = "$1" ] && return 0
  done
  return 1
}

TARGET_DIR=""
TARGET_EXPLICIT=0
MODE="link"
PROJECT_DIR=""
HARNESS="generic"
HARNESS_EXPLICIT=0
FORCE=0
DRY_RUN=0
COPIED=0
REPO_DIR="$(script_dir)"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || die "--target requires a directory"
      TARGET_DIR="$2"
      TARGET_EXPLICIT=1
      shift 2
      ;;
    --mode)
      [ "$#" -ge 2 ] || die "--mode requires link or copy"
      MODE="$2"
      shift 2
      ;;
    --project)
      [ "$#" -ge 2 ] || die "--project requires a directory"
      PROJECT_DIR="$2"
      shift 2
      ;;
    --harness)
      [ "$#" -ge 2 ] || die "--harness requires a comma-separated list or 'all'"
      HARNESS="$2"
      HARNESS_EXPLICIT=1
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

{ [ -d "$REPO_DIR/procedures" ] || [ -d "$REPO_DIR/tools" ]; } || die "cannot find procedures/ or tools/ under $REPO_DIR"

# Are we running from inside the repo tree, or from some other working directory?
PWD_RESOLVED="$(pwd -P)"
case "$PWD_RESOLVED/" in
  "$REPO_DIR/"*) INSIDE_REPO=1 ;;
  *) INSIDE_REPO=0 ;;
esac

case "$MODE" in
  link|copy) ;;
  *) die "--mode must be link or copy" ;;
esac

for _h in $(harness_list); do
  case "$_h" in
    claude|claudecode|codex|zcode|kimi|qwen|pi|opencode|generic) ;;
    *) die "unknown harness '$_h' (valid: $ALL_HARNESSES generic, or all)" ;;
  esac
done

if [ -z "$TARGET_DIR" ]; then
  if [ -n "${CODEX_HOME:-}" ]; then
    TARGET_DIR="$CODEX_HOME/skills"
    [ "$HARNESS_EXPLICIT" -eq 1 ] || HARNESS="codex"
  elif [ -d "$HOME/.codex" ]; then
    TARGET_DIR="$HOME/.codex/skills"
    [ "$HARNESS_EXPLICIT" -eq 1 ] || HARNESS="codex"
  else
    TARGET_DIR="$HOME/.claude/skills"
    [ "$HARNESS_EXPLICIT" -eq 1 ] || HARNESS="claude"
  fi
fi

# Resolve user-supplied and default destinations against the original working
# directory before any later cd. Absolute (even if lexically containing "..") is
# sufficient for safe symlink targets and registry entries when the leaf does not
# exist yet.
absolute_from_original_cwd() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$PWD_RESOLVED" "$1" ;;
  esac
}

TARGET_DIR="$(absolute_from_original_cwd "$TARGET_DIR")"
if [ -n "$PROJECT_DIR" ]; then
  PROJECT_DIR="$(absolute_from_original_cwd "$PROJECT_DIR")"
fi

run() {
  printf '%s\n' "$*"
  if [ "$DRY_RUN" -eq 0 ]; then
    "$@"
  fi
}

mkdir_if_needed() {
  if [ ! -d "$1" ]; then
    run mkdir -p "$1"
  fi
}

set_aicc_state_paths() {
  _aicc_state_base="${XDG_STATE_HOME:-$HOME/.local/state}"
  case "$_aicc_state_base" in
    /*) ;;
    *)
      printf 'ERROR: XDG_STATE_HOME must be absolute: %s\n' "$_aicc_state_base" >&2
      return 1
      ;;
  esac
  AICC_STATE_DIR="$_aicc_state_base/aicc"
  AICC_REGISTRY_FILE="$AICC_STATE_DIR/registry"
  AICC_DEFAULT_FILE="$AICC_STATE_DIR/default"
  AICC_TAB="$(printf '\t')"
}

check_aicc_state_path() {
  _aicc_check_path="$1"
  _aicc_check_label="$2"
  if [ -L "$_aicc_check_path" ]; then
    printf 'ERROR: refusing symlinked AICC %s: %s\n' \
      "$_aicc_check_label" "$_aicc_check_path" >&2
    return 1
  fi
  if [ -e "$_aicc_check_path" ] && [ ! -f "$_aicc_check_path" ]; then
    printf 'ERROR: AICC %s is not a regular file: %s\n' \
      "$_aicc_check_label" "$_aicc_check_path" >&2
    return 1
  fi
}

ensure_aicc_state() {
  set_aicc_state_paths || return 1
  if [ -L "$AICC_STATE_DIR" ]; then
    printf 'ERROR: refusing symlinked AICC state directory: %s\n' \
      "$AICC_STATE_DIR" >&2
    return 1
  fi
  if [ -e "$AICC_STATE_DIR" ] && [ ! -d "$AICC_STATE_DIR" ]; then
    printf 'ERROR: AICC state path is not a directory: %s\n' \
      "$AICC_STATE_DIR" >&2
    return 1
  fi
  check_aicc_state_path "$AICC_REGISTRY_FILE" registry || return 1
  check_aicc_state_path "$AICC_DEFAULT_FILE" default || return 1

  if [ "$DRY_RUN" -eq 1 ]; then
    printf 'ensure AICC state: %s (mode 0700; files mode 0600)\n' \
      "$AICC_STATE_DIR"
    return 0
  fi

  mkdir -p "$AICC_STATE_DIR" || return 1
  [ ! -L "$AICC_STATE_DIR" ] || {
    printf 'ERROR: AICC state directory became a symlink: %s\n' \
      "$AICC_STATE_DIR" >&2
    return 1
  }
  chmod 0700 "$AICC_STATE_DIR" || return 1
  [ ! -e "$AICC_REGISTRY_FILE" ] || chmod 0600 "$AICC_REGISTRY_FILE" || return 1
  [ ! -e "$AICC_DEFAULT_FILE" ] || chmod 0600 "$AICC_DEFAULT_FILE" || return 1
}

registry_value_is_safe() {
  case "$1" in
    *"$AICC_TAB"*|*'
'*) return 1 ;;
    *) return 0 ;;
  esac
}

collection_has_aicc_cli() {
  [ -f "$1/aicc/aicc.py" ] &&
    [ -d "$1/procedures" ] &&
    [ -d "$1/tools" ]
}

# register_aicc_collection project|shared <project-root-or-dash> <collection>
register_aicc_collection() {
  _aicc_kind="$1"
  _aicc_project_root="$2"
  _aicc_collection="$3"

  ensure_aicc_state || return 1
  case "$_aicc_kind" in
    project)
      case "$_aicc_project_root" in
        /*) ;;
        *)
          printf 'ERROR: project registry root must be absolute: %s\n' \
            "$_aicc_project_root" >&2
          return 1
          ;;
      esac
      ;;
    shared) _aicc_project_root="-" ;;
    *)
      printf 'ERROR: unknown AICC registry kind: %s\n' "$_aicc_kind" >&2
      return 1
      ;;
  esac
  case "$_aicc_collection" in
    /*) ;;
    *)
      printf 'ERROR: collection registry path must be absolute: %s\n' \
        "$_aicc_collection" >&2
      return 1
      ;;
  esac
  registry_value_is_safe "$_aicc_project_root" || {
    printf 'ERROR: project path contains a tab or newline and cannot be registered\n' >&2
    return 1
  }
  registry_value_is_safe "$_aicc_collection" || {
    printf 'ERROR: collection path contains a tab or newline and cannot be registered\n' >&2
    return 1
  }

  if [ "$DRY_RUN" -eq 1 ]; then
    if ! collection_has_aicc_cli "$_aicc_collection" && [ "$COPIED" -ne 1 ]; then
      printf 'ERROR: collection would remain invalid without --force: %s\n' \
        "$_aicc_collection" >&2
      return 1
    fi
    if [ "$_aicc_kind" = project ]; then
      printf 'register AICC project: %s -> %s (%s)\n' \
        "$_aicc_project_root" "$_aicc_collection" "$AICC_REGISTRY_FILE"
    else
      printf 'register AICC shared collection: %s (%s)\n' \
        "$_aicc_collection" "$AICC_REGISTRY_FILE"
      printf 'update AICC default: %s -> %s\n' \
        "$AICC_DEFAULT_FILE" "$_aicc_collection"
    fi
    return 0
  fi

  if ! collection_has_aicc_cli "$_aicc_collection"; then
    printf 'ERROR: refusing to register invalid AICC collection: %s\n' \
      "$_aicc_collection" >&2
    return 1
  fi

  _aicc_registry_tmp="$(mktemp "$AICC_STATE_DIR/.registry.tmp.XXXXXX")" || return 1
  chmod 0600 "$_aicc_registry_tmp" || {
    rm -f "$_aicc_registry_tmp"
    return 1
  }
  if [ -f "$AICC_REGISTRY_FILE" ]; then
    while IFS="$AICC_TAB" read -r _old_kind _old_root _old_collection _old_extra; do
      [ -z "$_old_extra" ] || continue
      case "$_old_kind" in
        project)
          [ "$_aicc_kind" = project ] && \
            [ "$_old_root" = "$_aicc_project_root" ] && continue
          ;;
        shared)
          [ "$_aicc_kind" = shared ] && \
            [ "$_old_collection" = "$_aicc_collection" ] && continue
          ;;
        *) continue ;;
      esac
      printf '%s\t%s\t%s\n' \
        "$_old_kind" "$_old_root" "$_old_collection" >> "$_aicc_registry_tmp"
    done < "$AICC_REGISTRY_FILE"
  fi
  printf '%s\t%s\t%s\n' \
    "$_aicc_kind" "$_aicc_project_root" "$_aicc_collection" >> "$_aicc_registry_tmp"

  check_aicc_state_path "$AICC_REGISTRY_FILE" registry || {
    rm -f "$_aicc_registry_tmp"
    return 1
  }
  mv "$_aicc_registry_tmp" "$AICC_REGISTRY_FILE" || {
    rm -f "$_aicc_registry_tmp"
    return 1
  }
  chmod 0600 "$AICC_REGISTRY_FILE" || return 1

  if [ "$_aicc_kind" = shared ]; then
    _aicc_default_tmp="$(mktemp "$AICC_STATE_DIR/.default.tmp.XXXXXX")" || return 1
    chmod 0600 "$_aicc_default_tmp" || {
      rm -f "$_aicc_default_tmp"
      return 1
    }
    printf '%s\n' "$_aicc_collection" > "$_aicc_default_tmp" || {
      rm -f "$_aicc_default_tmp"
      return 1
    }
    check_aicc_state_path "$AICC_DEFAULT_FILE" default || {
      rm -f "$_aicc_default_tmp"
      return 1
    }
    mv "$_aicc_default_tmp" "$AICC_DEFAULT_FILE" || {
      rm -f "$_aicc_default_tmp"
      return 1
    }
    chmod 0600 "$AICC_DEFAULT_FILE" || return 1
  fi
}

# Install a small user-facing locator launcher while keeping the Python helper and
# its PEP 723 dependency metadata inside a stable collection copy. The launcher is
# deliberately collection-neutral: installing another self-contained project must
# not silently rebind the global command to that project's absolute path.
install_aicc_cli() {
  _collection="$1"
  _script="$_collection/aicc/aicc.py"
  _launcher_source="$REPO_DIR/aicc/launcher.sh"
  _bin_dir="$HOME/.local/bin"
  _cli="$_bin_dir/aicc"
  _marker="# managed-by: auto-computational-chemist/install.sh"

  # --force applies to collection/skill refreshes, never to an unrelated command
  # that happens to have the same name. Only a launcher with our exact marker in
  # the expected line is safe to update in place.
  if [ -L "$_cli" ]; then
    printf 'WARNING: existing launcher symlink left untouched: %s\n' "$_cli" >&2
    return 0
  fi
  if [ -e "$_cli" ]; then
    if [ ! -f "$_cli" ]; then
      printf 'WARNING: existing non-file launcher left untouched: %s\n' "$_cli" >&2
      return 0
    fi
    if [ "$(sed -n '2{p;q;}' "$_cli" 2>/dev/null || :)" != "$_marker" ]; then
      printf 'WARNING: existing non-AICC launcher left untouched: %s\n' "$_cli" >&2
      return 0
    fi
  fi

  if [ ! -f "$_launcher_source" ]; then
    printf 'WARNING: AICC launcher source is missing: %s\n' "$_launcher_source" >&2
    return 1
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    if ! collection_has_aicc_cli "$_collection" && [ "$COPIED" -ne 1 ]; then
      printf 'WARNING: aicc CLI would remain unavailable from stale collection: %s\n' \
        "$_collection" >&2
      return 0
    fi
    printf 'install CLI: %s (universal collection locator)\n' "$_cli"
    return 0
  fi

  if [ ! -f "$_script" ]; then
    printf 'WARNING: aicc CLI source is missing from %s; re-run with --force to refresh the collection copy.\n' "$_collection" >&2
    return 0
  fi

  mkdir -p "$_bin_dir" || return 1
  _tmp="$(mktemp "$_bin_dir/.aicc.tmp.XXXXXX")" || return 1
  if ! cp "$_launcher_source" "$_tmp"; then
    rm -f "$_tmp"
    return 1
  fi
  chmod +x "$_tmp" || { rm -f "$_tmp"; return 1; }
  mv "$_tmp" "$_cli" || { rm -f "$_tmp"; return 1; }
  printf 'Installed CLI: %s\n' "$_cli"

  case ":${PATH:-}:" in
    *:"$_bin_dir":*) ;;
    *) printf 'Add %s to PATH to use `aicc` directly.\n' "$_bin_dir" ;;
  esac
}

# link_rel <dest> <target> : symlink, honoring --force, skipping (return 1) if dest exists.
link_rel() {
  _dest="$1"
  _target="$2"
  if [ -e "$_dest" ] || [ -L "$_dest" ]; then
    if [ "$FORCE" -eq 1 ]; then
      run rm -rf "$_dest"
    else
      printf 'skip existing: %s (use --force to replace)\n' "$_dest"
      return 1
    fi
  fi
  run ln -s "$_target" "$_dest"
  return 0
}

# copy_collection <dest> : copy aicc/ procedures/ tools/ knowledge/ + top docs (no .git/dev).
# Sets COPIED=1 if it (re)copied, 0 if it skipped.
copy_collection() {
  _dest="$1"
  COPIED=0
  _planned_remove=0
  if [ -e "$_dest" ] && [ "$FORCE" -eq 1 ]; then
    run rm -rf "$_dest"
    _planned_remove=1
  fi
  if [ -e "$_dest" ] && [ "$_planned_remove" -eq 0 ]; then
    printf 'ERROR: refusing to reuse existing collection: %s\n' "$_dest" >&2
    printf '%s\n' 'Re-run with --force to replace it from this trusted source.' >&2
    return 1
  fi
  run mkdir -p "$_dest"
  for item in aicc procedures tools knowledge AGENTS.md STRUCTURE.md README.md; do
    [ -e "$REPO_DIR/$item" ] || continue
    run cp -R "$REPO_DIR/$item" "$_dest/$item"
  done
  COPIED=1
}

# rewrite_refs <collection_dir> : rewrite root-relative knowledge//tools//procedures/
# refs in the copy's *.md files to absolute paths based at <collection_dir>. Idempotent.
rewrite_refs() {
  _coll="$1"
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'WARNING: python3 not found; skipping absolute-path rewrite -- knowledge/ refs\n' >&2
    printf '         stay relative and rely on symlink-following/CWD. Install python3 + re-run.\n' >&2
    return 0
  fi
  printf 'rewriting cross-refs to absolute base: %s\n' "$_coll"
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '(dry-run: would rewrite knowledge//tools//procedures/ refs in *.md)\n'
    return 0
  fi
  python3 - "$_coll" <<'PY'
import os, re, sys
base = os.path.realpath(sys.argv[1])
pat = re.compile(r'(?<![\w./-])(knowledge|tools|procedures)/')
changed = 0
for root, _dirs, files in os.walk(base):
    for f in files:
        if not f.endswith(".md"):
            continue
        p = os.path.join(root, f)
        try:
            s = open(p, encoding="utf-8").read()
        except Exception:
            continue
        n = pat.sub(lambda m: base + "/" + m.group(1) + "/", s)
        if n != s:
            open(p, "w", encoding="utf-8").write(n)
            changed += 1
print("  rewrote refs in %d markdown file(s)" % changed)
PY
}

# install_skill_into <src-skill-dir> <discovery-dir> : symlink (or copy) one skill.
install_skill_into() {
  _src="$1"
  _into="$2"
  _name="$(basename "$_src")"
  _dest="$_into/$_name"
  if [ -e "$_dest" ] || [ -L "$_dest" ]; then
    if [ "$FORCE" -eq 1 ]; then
      run rm -rf "$_dest"
    else
      printf 'skip existing skill: %s (use --force to replace)\n' "$_dest"
      return 1
    fi
  fi
  if [ "$MODE" = "link" ]; then
    run ln -s "$_src" "$_dest"
  else
    run cp -R "$_src" "$_dest"
  fi
  return 0
}

# install_project_file <collection_dir> : drop instruction file(s) into --project, per --harness.
install_project_file() {
  [ -n "$PROJECT_DIR" ] || return 0
  [ -d "$PROJECT_DIR" ] || die "--project directory does not exist: $PROJECT_DIR"
  _coll="$1"
  link_rel "$PROJECT_DIR/AGENTS.md" "$_coll/AGENTS.md" || :
  if has_harness claude; then link_rel "$PROJECT_DIR/CLAUDE.md" "$_coll/AGENTS.md" || :; fi
  if has_harness qwen; then link_rel "$PROJECT_DIR/QWEN.md" "$_coll/AGENTS.md" || :; fi
}

install_to_cwd() {
  collection_dir="$PWD_RESOLVED/.auto-computational-chemist"
  skills_dir="$PWD_RESOLVED/.agents/skills"

  printf 'Self-contained install into %s\n' "$PWD_RESOLVED"
  printf '  collection copy : %s\n' "$collection_dir"
  printf '  harnesses       : %s\n\n' "$(harness_list)"

  copy_collection "$collection_dir" || die "could not create trusted collection copy"
  [ "$COPIED" -eq 1 ] && rewrite_refs "$collection_dir"

  # Canonical skill store (.agents/skills) + base instruction (AGENTS.md).
  mkdir_if_needed "$skills_dir"
  count=0
  for skill_dir in "$REPO_DIR"/procedures/* "$REPO_DIR"/tools/*; do
    [ -f "$skill_dir/SKILL.md" ] || continue
    name="$(basename "$skill_dir")"
    parent="$(basename "$(dirname "$skill_dir")")"
    if install_skill_into "$collection_dir/$parent/$name" "$skills_dir"; then
      count=$((count + 1))
    fi
  done
  link_rel "$PWD_RESOLVED/AGENTS.md" "$collection_dir/AGENTS.md" || :

  # Per-harness aliases -> the canonical .agents/skills + AGENTS.md.
  if has_harness claude; then
    mkdir_if_needed "$PWD_RESOLVED/.claude"
    link_rel "$PWD_RESOLVED/.claude/skills" "../.agents/skills" || :
    link_rel "$PWD_RESOLVED/CLAUDE.md" "AGENTS.md" || :
  fi
  if has_harness qwen; then
    mkdir_if_needed "$PWD_RESOLVED/.qwen"
    link_rel "$PWD_RESOLVED/.qwen/skills" "../.agents/skills" || :
    link_rel "$PWD_RESOLVED/QWEN.md" "AGENTS.md" || :
  fi
  if has_harness zcode; then
    mkdir_if_needed "$PWD_RESOLVED/.zcode"
    link_rel "$PWD_RESOLVED/.zcode/skills" "../.agents/skills" || :
  fi

  install_project_file "$collection_dir"
  register_aicc_collection project "$PWD_RESOLVED" "$collection_dir" || \
    die "could not register self-contained AICC collection"
  if ! install_aicc_cli "$collection_dir"; then
    printf 'WARNING: could not install the optional aicc launcher; skills were installed successfully.\n' >&2
  fi

  printf '\nInstalled %s skills; canonical store: .agents/skills/ ; refs rewritten absolute under %s\n' "$count" "$collection_dir"
  printf 'Discovery wired for:\n'
  has_harness codex    && printf '  codex     -> .agents/skills/  + AGENTS.md\n'    || :
  has_harness kimi     && printf '  kimi      -> .agents/skills/  + AGENTS.md\n'    || :
  has_harness pi       && printf '  pi        -> .agents/skills/  + AGENTS.md\n'    || :
  has_harness opencode && printf '  opencode  -> .agents/skills/  + AGENTS.md\n'    || :
  has_harness claude   && printf '  claude    -> .claude/skills/  + CLAUDE.md\n'    || :
  has_harness qwen     && printf '  qwen      -> .qwen/skills/ (+ .agents) + QWEN.md/AGENTS.md\n' || :
  has_harness zcode    && printf '  zcode     -> .zcode/skills/ (UNVERIFIED) + AGENTS.md; reliable path is global ~/.zcode/skills or in-app import\n' || :
  printf 'NOTE: absolute refs -> project is not movable (re-run install if relocated).\n'
  printf '      kimi anchors skill discovery at the nearest .git -- run `git init` here if needed.\n'
  printf 'Next: restart/refresh the agent so it reloads skill metadata.\n'
}

# Validate the user-private launcher state before changing any collection or skill
# paths, so a bad/symlinked registry cannot leave a half-installed skill tree.
ensure_aicc_state || die "could not prepare AICC launcher state"

# ---- Outside the repo with no explicit --target: self-contained, multi-harness. ----
if [ "$INSIDE_REPO" -eq 0 ] && [ "$TARGET_EXPLICIT" -eq 0 ]; then
  [ "$HARNESS_EXPLICIT" -eq 1 ] || HARNESS="all"
  install_to_cwd
  exit 0
fi

# ---- Shared install (inside the repo, or explicit --target). ----
collection_dir="$(dirname "$TARGET_DIR")/.auto-computational-chemist"
printf 'Shared install\n'
printf '  skills target   : %s\n' "$TARGET_DIR"
printf '  collection copy : %s\n\n' "$collection_dir"

copy_collection "$collection_dir" || die "could not create trusted collection copy"
[ "$COPIED" -eq 1 ] && rewrite_refs "$collection_dir"

mkdir_if_needed "$TARGET_DIR"
installed=0
for skill_dir in "$REPO_DIR"/procedures/* "$REPO_DIR"/tools/*; do
  [ -f "$skill_dir/SKILL.md" ] || continue
  name="$(basename "$skill_dir")"
  parent="$(basename "$(dirname "$skill_dir")")"
  if install_skill_into "$collection_dir/$parent/$name" "$TARGET_DIR"; then
    installed=$((installed + 1))
  fi
done

install_project_file "$collection_dir"
register_aicc_collection shared - "$collection_dir" || \
  die "could not register shared AICC collection"
if ! install_aicc_cli "$collection_dir"; then
  printf 'WARNING: could not install the optional aicc launcher; skills were installed successfully.\n' >&2
fi

printf '\nInstalled %s skills into %s\n' "$installed" "$TARGET_DIR"
printf 'Collection copy : %s  (.git/ and dev/ excluded; cross-refs rewritten to absolute)\n' "$collection_dir"
printf 'Mode: %s   Harness: %s\n' "$MODE" "$HARNESS"
printf 'NOTE: copy+absolute means `git pull` no longer auto-propagates; re-run install to update.\n'
printf 'Next: restart or refresh the agent session so it reloads skill metadata.\n'
