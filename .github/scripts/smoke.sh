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

# inspect must be valid JSON and must not touch the project
before="$(cd ci-smoke && find . -type f | sort)"
(cd ci-smoke && "$spawn" inspect . --json) | "$bin/python" -c 'import json,sys; assert "schema_version" in json.load(sys.stdin)'
(cd ci-smoke && "$spawn" onboard . --json) | "$bin/python" -c 'import json,sys; r=json.load(sys.stdin); assert r["schema_version"] == "1.0" and r["repository"]["name"] == "ci-smoke" and "commands" in r'
after="$(cd ci-smoke && find . -type f | sort)"
[ "$before" = "$after" ] || { echo "inspect changed ci-smoke" >&2; exit 1; }

expect_exit() {
  want="$1"; shift
  set +e; "$@" > /dev/null 2>&1; got=$?; set -e
  [ "$got" -eq "$want" ] || { echo "'$*' exited $got, expected $want" >&2; exit 1; }
}
expect_exit 1 "$spawn" create --name x --template nope
expect_exit 2 "$spawn" create --bogus
expect_exit 7 "$spawn" onboard missing --json

mkdir -p diagnose-smoke/tests diagnose-partial
printf '[project]\nname = "diagnose-smoke"\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n' > diagnose-smoke/pyproject.toml
(cd diagnose-smoke && "$spawn" diagnose --json) |
  "$bin/python" -c 'import json,sys; r=json.load(sys.stdin); assert r["schema_version"] == "1.0" and r["status"] == "complete" and r["is_clean"]'
printf '[project]\nname = "diagnose-smoke"\n[tool.pytest.ini_options]\ntestpaths = ["missing"]\n' > diagnose-smoke/pyproject.toml
expect_exit 8 "$spawn" diagnose diagnose-smoke --json --fail-on warning
printf '[project]\nname = "diagnose-partial"\n[tool.pytest.ini_options]\ntestpaths = ["tests/*"]\n' > diagnose-partial/pyproject.toml
expect_exit 9 "$spawn" diagnose diagnose-partial --json --fail-on warning
expect_exit 7 "$spawn" diagnose missing --json
echo "smoke OK"
