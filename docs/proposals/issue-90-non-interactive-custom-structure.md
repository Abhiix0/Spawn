# Design Proposal: Non-Interactive Input Format for Custom Structure

* **Issue**: #90 (P3 | Enhancement)
* **Component**: `spawn.generators.custom_structure`, `spawn.cli`
* **Status**: Proposed (Design Only — Target: v1.2.0)

---

## 1. Overview and Problem Statement

`spawn create --template custom` currently operates as an interactive workflow: users paste folder-structure text (Unix tree, Markdown list, or indented hierarchy) into a prompt, optionally review parsed results, and select configuration extras.

For automated environments, script orchestration, and CI/CD pipelines, interactive prompts are unavailable. A non-interactive input format is needed so that developers and build pipelines can provision custom directory hierarchies deterministically from file specifications or standard input.

---

## 2. CLI Interface & Flags

To maintain compatibility with Typer and existing non-interactive conventions in Spawn, the following flags are proposed for `spawn create`:

```bash
# File-based input
spawn create --name my-app --template custom --structure-file ./layout.txt --yes

# Short option alias
spawn create --name my-app --template custom -f ./layout.md --yes

# Standard input pipe
cat layout.tree | spawn create --name my-app --template custom --structure-file - --yes

# Explicit format specification (default: 'auto')
spawn create --name my-app --template custom -f layout.txt --structure-format indented --yes

# Non-interactive preview (dry-run)
spawn create --name my-app --template custom -f layout.txt --dry-run
```

### Proposed CLI Parameters
* `--structure-file`, `-f`: Path to a file containing the structure definition, or `-` for `stdin`.
* `--structure-format`: Optional format selector (`auto`, `tree`, `markdown`, `indented`). Defaults to `auto`.
* `--dependency`: Repeatable string flag (`--dependency fastapi --dependency pydantic`) or comma-separated list (`-d "fastapi,uvicorn"`) for runtime dependencies.
* `--dev-setup`: Repeatable or comma-separated quality extras: `ruff`, `pytest`, `precommit`, `mypy`.

---

## 3. Supported Structure Formats & Schema Validation

The input specification supports plain text files matching Spawn's three established formats:

1. **Unix Tree Output** (`format: tree`):
   ```text
   my-app/
   ├── src/
   │   ├── __init__.py
   │   └── main.py
   ├── tests/
   │   └── test_app.py
   ├── pyproject.toml
   └── README.md
   ```
2. **Markdown List** (`format: markdown`):
   ```markdown
   - src/
     - __init__.py
     - main.py
   - tests/
     - test_app.py
   - pyproject.toml
   - README.md
   ```
3. **Indented Plain Text** (`format: indented`):
   ```text
   src/
       __init__.py
       main.py
   tests/
       test_app.py
   pyproject.toml
   README.md
   ```

### Validation Rules
* **Max Size**: Maximum allowed input file size is 1 MB (protects against memory exhaustion).
* **Encoding**: Must be valid UTF-8. Non-UTF-8 inputs raise `InvalidInputError("Structure file must be valid UTF-8")`.
* **Empty Input**: Empty or whitespace-only files raise `StructureParseError("Input is empty — no structure to parse.")`.
* **Parsing Validation**: Reuses existing `parse_structure()` from `spawn.generators.custom_structure`.
* **Path Disambiguation**:
  * Trailing `/` explicitly denotes a directory (even if named `config.d/`).
  * Files without extensions matching `_KNOWN_EXTENSIONLESS_FILES` (`Dockerfile`, `LICENSE`, `Makefile`) are correctly identified as files.

---

## 4. Path Traversal & Filesystem Safety

Security constraints enforced during parsing and path resolution:

1. **Character Validation**:
   * Windows path separators (`\`) in names are rejected with `StructureParseError` (forward slashes `/` are canonical).
   * Null bytes (`\0`) and Windows drive letters (`C:`) are rejected immediately.
2. **Directory Escape Prevention**:
   * Segment checks reject `..` in relative paths.
   * `safe_join(project_path, entry.path)` ensures the resolved path strictly resides within the target project root using `resolve().is_relative_to(project_path.resolve())`.
3. **Junction & Symlink Traversal Protection**:
   * Leverages `assert_available()` to prevent creating projects into existing symlinks or Windows junctions.
   * Atomic rollback cleanup tracks created files via ownership tokens.

---

## 5. Duplicate and Conflicting Paths Handling

* **Exact Duplicate Paths**: If two lines resolve to the same relative path (e.g., duplicate `src/main.py`), `parse_structure` raises:
  ```text
  StructureParseError: Duplicate path in structure: 'src/main.py'
  ```
* **Directory/File Conflicts**: If an entry specifies `app/` as a directory and another specifies `app` as a file, the parser detects the type conflict and raises `StructureParseError("Conflicting entry type for path: 'app'")`.

---

## 6. Dry-Run & Preview Mechanism

When `--dry-run` is passed with `--structure-file`:
1. Validates CLI flags and reads structure file/stdin.
2. Parses structure into `list[ParsedEntry]`.
3. Validates target availability.
4. Renders a formatted `rich.tree.Tree` preview of the hierarchy to `stdout`.
5. Exits cleanly with code `0` without creating any directories or touching disk.

---

## 7. Integration with Existing Architecture

* **Models**: Directly passes `parsed_entries` to `ProjectConfig(template="custom", custom_entries=entries, ...)`.
* **Generator**: Invokes `CustomStructureGenerator.generate(...)` without modification.
* **Pipeline**: Integrates with `spawn.generators.pipeline.generate_project()`.

---

## 8. CI/Script Compatibility & Exit Codes

| Exit Code | Condition |
|---|---|
| `0` | Successful generation or clean `--dry-run`. |
| `1` | File not found, permission denied reading structure file, or invalid arguments. |
| `3` | Destination directory already exists or filesystem error (`FilesystemError`). |
| `5` | Structure parse error (`StructureParseError` — malformed indentation, duplicate path, path traversal attempt). |

---

## 9. Proposed Regression Test Suite

1. `test_noninteractive_tree_file_success(tmp_path)`: Reads valid tree file and creates full structure.
2. `test_noninteractive_markdown_file_success(tmp_path)`: Reads markdown list file.
3. `test_noninteractive_indented_file_success(tmp_path)`: Reads indented file.
4. `test_noninteractive_stdin_pipe(tmp_path)`: Pipes structure through stdin (`--structure-file -`).
5. `test_noninteractive_dry_run_writes_nothing(tmp_path)`: Asserts no disk writes on `--dry-run`.
6. `test_noninteractive_rejects_missing_file()`: Exits 1 on non-existent structure file.
7. `test_noninteractive_rejects_path_traversal()`: Exits 5 when file contains `../`.
8. `test_noninteractive_rejects_duplicate_paths()`: Exits 5 when file contains identical relative paths.
