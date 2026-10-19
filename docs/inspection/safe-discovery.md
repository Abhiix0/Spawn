# Safe Repository Discovery (#54)

Implementation: `spawn.inspection.discovery`. This module performs *filesystem
inventory only*. It does not parse manifests, import project modules, execute
commands, access the network, or write to an inspected project. The inventory
uses the existing `DiscoveryInventory` and `Diagnostic` types from the #53
contract (called “Issue #1” in some v1.1.0 planning instructions).

```python
from spawn.inspection.discovery import discover_repository, validate_inspection_root

inventory = discover_repository("./existing-project")
# or: discover_repository(validate_inspection_root("./existing-project"))
```

- Roots are resolved to absolute directories and checked with `scandir`.
  Invalid or inaccessible roots raise `InspectionError(exit_code=7)`.
  An explicitly supplied root symlink is resolved once; descendants are not.
- Entries are examined without following symlinks; **neither file nor directory
  symlinks are included**. Broken links, self-loops, and out-of-root links are
  skipped with `discovery.symlink_skipped` informational diagnostics. Windows
  junctions are also skipped.
- Nested directory traversal is sorted by name; output `files`, `directories`,
  and `skipped` are sorted relative POSIX-style paths (`a/b.py`). Entries of
  excluded directories are not visited. The root itself is not listed.
  Spaces, Unicode, and punctuation in names are preserved. On POSIX, a literal
  backslash in a filename remains a backslash character, **not** a separator.
  The implementation uses an explicit work stack rather than recursive Python
  calls; very deep trees are still subject to host filesystem path limits.
- Default excluded directory basenames, at any depth (case-insensitive):
  `.git`, `.hg`, `.svn`, `node_modules`, `vendor`, `dist`, `build`,
  `coverage`, `htmlcov`, `target`, `.next`, `.nuxt`, `.cache`, `.turbo`,
  `__pycache__`, `.venv`, `venv`, `env`, `.uv`, `.tox`, `.nox`,
  `.pytest_cache`, `.ruff_cache`, `.mypy_cache`.  These include Spawn's own
  ignored virtual-environment, test, build, and cache directories, plus
  common third-party dependency/build directories.  This is **not** a full
  `.gitignore` parser: files such as `.spawn/meta.json` and configuration
  under `.github` remain visible to evidence-based analyzers.
- Custom exclusions replace the defaults: `discover_repository(path,
  excluded_directories={"private", "target"})`. Pass `()` to include the
  default-excluded directories; a single string such as `"private"` is
  accepted as shorthand. Only single directory basenames are supported.
- Skipped symlinks, unsupported entry types, missing entries and permission /
  IO errors are associated with a `Diagnostic` including a relative `path`.
  Deliberate directory exclusions appear in `skipped` **without diagnostics**,
  to avoid giving every normal repository a `PARTIAL` status just for `.git`.
  Discovery never opens ordinary files; file-content readability is the
  consuming analyzer's responsibility.
- On POSIX systems with supported dirfd operations, scanning starts from an
  anchored root descriptor; nested directories are re-opened relative to it
  with `O_NOFOLLOW`. This closes the typical symlink-swap escape race and
  avoids file-descriptor exhaustion. On platforms without these APIs the
  implementation verifies directories remain under the resolved root and
  rejects junctions/symlinks before descending. That path-based fallback is
  **not race-proof** against an attacker concurrently changing directories.
  A symlink swap detected during descriptor-based descent yields
  `discovery.symlink_race`, including Linux systems where `O_DIRECTORY` reports
  `ENOTDIR` rather than `ELOOP`.  As with any filesystem walk, concurrent
  mutations can change results. File symlink targets are never opened to check
  their permissions or contents, including inaccessible targets.

## Diagnostic codes

| Code | Meaning |
|---|---|
| `discovery.symlink_skipped` | Symbolic link or junction deliberately not followed |
| `discovery.permission_denied` | Entry cannot be accessed because of permissions |
| `discovery.entry_disappeared` | Entry removed or ceased to be a directory during scan |
| `discovery.symlink_race` | Directory became a symbolic link while descending |
| `discovery.filesystem_error` | Other recoverable filesystem problem |
| `discovery.unsupported_entry_type` | Socket, FIFO, device or other non-file/dir entry |

## Integration notes / outstanding #53 decision

The approved #53 Python model defines `DiscoveryInventory.skipped` as
`tuple[str, ...]`, not `(path, reason)` pairs. The sign-off for that format
remains marked **NEEDS SIGN-OFF** in the contract. Consumers should obtain
reason details from a corresponding diagnostic where emitted and recognize
normal exclusions from the shared excluded set. Do not change the report
schema in #54; request final approval from the #53 contract owner.

Issue #58 (orchestrator) should call this module once and share its returned
inventory with all analyzers. Issue #59 owns CLI wiring; #54 adds no command.

## Coordination note for GMA / downstream analyzer owners

The smallest required inter-module interface remains the checked-in #53 model:

```python
inventory = discover_repository(target)  # target: str | Path | InspectionTarget
# inventory.files, inventory.directories, inventory.skipped: tuple[str, ...]
# inventory.diagnostics: tuple[Diagnostic, ...]
```

GMA / #53 should confirm that `skipped` stays a plain path tuple and that
**intentional excludes** need no diagnostic, while errors and symlink skips
produce diagnostics. There is no new metadata field; #55 language/framework,
#56 dependency, and #57 tooling owners can use the file paths directly and
open only the relevant manifest/configuration files under `target.path`.
If additional metadata becomes essential, propose it through the shared
contract rather than silently extending discovery. #58 owns invoking discovery
once and sharing the inventory, and #59 owns CLI/JSON reporting. This text
is a proposed coordination message, **not** a claim that GMA has approved it.

## Merge-review verification (#54)

The regression fixtures explicitly verify retention of `.github/workflows/check.yml`,
`.spawn/meta.json`, `.devcontainer/devcontainer.json`, `pyproject.toml`,
`package.json`, `uv.lock`, `Dockerfile`, and nested hidden configuration files.
A separate fixture records directory scans and asserts generated, vendor, and
build subtrees are pruned before entry. The Windows-specific fixture attempts
to create a real directory junction; it skips when the host cannot do so.
POSIX tests simulate `ELOOP` and exercise an actual directory-to-symlink swap.

**Safety boundary:** discovery inventory paths are not stable file handles.
On supported POSIX platforms, the walker protects descent with directory
descriptors and `O_NOFOLLOW`; the path-based fallback is not race-proof.
Downstream analyzers reopening discovered paths must implement their own
file-open safety checks if concurrent hostile filesystem changes matter.

The #53 models remain unmodified. External sign-off from the contract owner
on `skipped` and intentional exclusions, and from #55, #56, #57, and #58
owners on path-only inventory sufficiency, remains necessary before merge.
