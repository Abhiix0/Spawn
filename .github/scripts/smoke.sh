#!/usr/bin/env bash
# Install the built wheel into a fresh venv and exercise the CLI.
# Usage: smoke.sh [EXPECTED_VERSION]   (run from the repo root after `uv build`)
set -euo pipefail

root="$PWD"
work="$(mktemp -d)"
uv venv "$work/venv"
if [ -d "$work/venv/Scripts" ]; then bin="$work/venv/Scripts"; else bin="$work/venv/bin"; fi
uv pip install --python "$work/venv" "$root"/dist/*.whl

spawn="$bin/spawn"
version_out="$("$spawn" version)"
echo "$version_out"
if [ -n "${1:-}" ]; then
  built="${version_out##*v}"
  if [ "$built" != "$1" ]; then
    echo "Built version '$built' does not match expected '$1'" >&2
    exit 1
  fi
fi
"$spawn" --help > /dev/null

cd "$work"
"$spawn" create --name ci-smoke --template mcp --no-git --no-uv --yes
for f in README.md AGENTS.md .spawn/meta.json; do
  test -f "ci-smoke/$f" || { echo "missing ci-smoke/$f" >&2; exit 1; }
done

expect_exit() {
  want="$1"; shift
  set +e; "$@" > /dev/null 2>&1; got=$?; set -e
  [ "$got" -eq "$want" ] || { echo "'$*' exited $got, expected $want" >&2; exit 1; }
}
expect_exit 1 "$spawn" create --name x --template nope
expect_exit 2 "$spawn" create --bogus
echo "smoke OK"
