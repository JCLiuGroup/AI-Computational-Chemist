#!/usr/bin/env sh
# managed-by: auto-computational-chemist/install.sh
set -eu

if ! command -v uv >/dev/null 2>&1; then
  echo "aicc: uv is required (https://docs.astral.sh/uv/)" >&2
  exit 127
fi

is_aicc_collection() {
  [ -n "${1:-}" ] &&
    [ -f "$1/aicc/aicc.py" ] &&
    [ -d "$1/procedures" ] &&
    [ -d "$1/tools" ]
}

run_collection() {
  requested_collection=$1
  shift
  selected_collection=$(cd "$requested_collection" 2>/dev/null && pwd -P) || {
    printf 'aicc: cannot resolve collection: %s\n' "$requested_collection" >&2
    return 1
  }
  if ! is_aicc_collection "$selected_collection"; then
    printf 'aicc: collection is no longer valid: %s\n' \
      "$selected_collection" >&2
    return 1
  fi
  AICC_COLLECTION=$selected_collection
  AICC_SOURCE=$selected_collection
  export AICC_COLLECTION AICC_SOURCE
  exec uv run "$selected_collection/aicc/aicc.py" "$@"
}

expand_home() {
  case "$1" in
    '~') printf '%s\n' "$HOME" ;;
    '~/'*) printf '%s/%s\n' "$HOME" "${1#\~/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

# Explicit overrides are authoritative. Fail loudly instead of silently running a
# different checkout when an operator requested a particular collection.
if [ -n "${AICC_COLLECTION:-}" ]; then
  override_value=$(expand_home "$AICC_COLLECTION")
  if is_aicc_collection "$override_value"; then
    run_collection "$override_value" "$@" || exit 2
  fi
  printf 'aicc: AICC_COLLECTION does not name a valid AICC collection: %s\n' \
    "$override_value" >&2
  exit 2
fi
if [ -n "${AICC_SOURCE:-}" ]; then
  override_value=$(expand_home "$AICC_SOURCE")
  if is_aicc_collection "$override_value"; then
    run_collection "$override_value" "$@" || exit 2
  fi
  printf 'aicc: AICC_SOURCE does not name a valid AICC collection: %s\n' \
    "$override_value" >&2
  exit 2
fi

# Project-local collections are executable only after this installer registered the
# absolute project root in private user state. Never execute an unregistered
# cwd/ancestor checkout.
state_base="${XDG_STATE_HOME:-$HOME/.local/state}"
case "$state_base" in
  /*) ;;
  *)
    printf 'aicc: XDG_STATE_HOME must be absolute: %s\n' "$state_base" >&2
    exit 2
    ;;
esac
state_dir="$state_base/aicc"
registry_file="$state_dir/registry"
default_file="$state_dir/default"
if [ -L "$state_dir" ]; then
  printf 'aicc: refusing symlinked state directory: %s\n' "$state_dir" >&2
  exit 2
fi
if [ -e "$state_dir" ] && [ ! -d "$state_dir" ]; then
  printf 'aicc: state path is not a directory: %s\n' "$state_dir" >&2
  exit 2
fi
for state_file in "$registry_file" "$default_file"; do
  if [ -L "$state_file" ]; then
    printf 'aicc: refusing symlinked state file: %s\n' "$state_file" >&2
    exit 2
  fi
  if [ -e "$state_file" ] && [ ! -f "$state_file" ]; then
    printf 'aicc: state path is not a regular file: %s\n' "$state_file" >&2
    exit 2
  fi
done

path_is_within() {
  [ "$1" = "$2" ] && return 0
  if [ "$2" = / ]; then
    case "$1" in /*) return 0 ;; esac
  else
    case "$1" in "$2"/*) return 0 ;; esac
  fi
  return 1
}

current_dir=$(pwd -P 2>/dev/null || pwd)
selected_project_root=
selected_project_collection=
selected_project_length=0
tab=$(printf '\t')
if [ -f "$registry_file" ]; then
  while IFS="$tab" read -r entry_kind entry_root entry_collection entry_extra; do
    [ "$entry_kind" = project ] || continue
    [ -z "$entry_extra" ] || continue
    case "$entry_root" in /*) ;; *) continue ;; esac
    case "$entry_collection" in /*) ;; *) continue ;; esac
    if path_is_within "$current_dir" "$entry_root"; then
      entry_length=${#entry_root}
      if [ "$entry_length" -gt "$selected_project_length" ]; then
        selected_project_root=$entry_root
        selected_project_collection=$entry_collection
        selected_project_length=$entry_length
      fi
    fi
  done < "$registry_file"
fi
if [ -n "$selected_project_collection" ]; then
  if is_aicc_collection "$selected_project_collection"; then
    run_collection "$selected_project_collection" "$@" || exit 2
  fi
  printf 'aicc: registered project collection is invalid: %s -> %s\n' \
    "$selected_project_root" "$selected_project_collection" >&2
  printf '%s\n' 'Re-run install.sh --force for this project.' >&2
  exit 2
fi

# A shared install atomically sets the collection-neutral default. A stale default
# is authoritative and fails loudly instead of silently selecting a different copy.
if [ -f "$default_file" ]; then
  candidate=
  IFS= read -r candidate < "$default_file" || :
  if [ -n "$candidate" ]; then
    case "$candidate" in
      /*) ;;
      *)
        printf 'aicc: registered default is not absolute: %s\n' "$candidate" >&2
        exit 2
        ;;
    esac
    if is_aicc_collection "$candidate"; then
      run_collection "$candidate" "$@" || exit 2
    fi
    printf 'aicc: registered default collection is invalid: %s\n' "$candidate" >&2
    printf '%s\n' 'Re-run a shared install.sh --force.' >&2
    exit 2
  fi
fi

# Compatibility fallback for conventional collections under the current user's
# home. These are bounded trusted locations, not arbitrary filesystem ancestors.
for candidate in \
  "${CODEX_HOME:-$HOME/.codex}/.auto-computational-chemist" \
  "$HOME/.codex/.auto-computational-chemist" \
  "$HOME/.claude/.auto-computational-chemist" \
  "$HOME/.auto-computational-chemist"
do
  if is_aicc_collection "$candidate"; then
    run_collection "$candidate" "$@" || exit 2
  fi
done

# Safe fallback for standard discovery directories: resolve the already-installed
# research-orchestrator skill symlink, then validate its collection before running.
for skills_dir in \
  "${CODEX_HOME:-$HOME/.codex}/skills" \
  "$HOME/.codex/skills" \
  "$HOME/.claude/skills"
do
  skill_dir="$skills_dir/research-orchestrator"
  if [ -d "$skill_dir" ]; then
    resolved_skill=$(cd "$skill_dir" 2>/dev/null && pwd -P) || resolved_skill=
    if [ -n "$resolved_skill" ]; then
      candidate=$(cd "$resolved_skill/../.." 2>/dev/null && pwd -P) || candidate=
      if is_aicc_collection "$candidate"; then
        run_collection "$candidate" "$@" || exit 2
      fi
    fi
  fi
done

printf '%s\n' 'aicc: cannot locate an AICC collection.' >&2
printf '%s\n' 'Register one with install.sh, install to a default Codex/Claude location,' >&2
printf '%s\n' 'or set AICC_COLLECTION (or AICC_SOURCE) to the collection root.' >&2
exit 1
