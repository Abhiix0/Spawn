# Security Policy

## Supported versions

Only the latest minor release of `spawnio` (currently 1.0.x) receives security fixes.

## Reporting a vulnerability

Please report vulnerabilities privately using GitHub's private vulnerability reporting: open the **Security** tab of [Abhiix0/Spawn](https://github.com/Abhiix0/Spawn) and choose **Report a vulnerability**. Do not open a public issue or discussion for security problems.

Include the Spawn version, your OS, and the smallest steps that reproduce the problem. Expect an acknowledgement on a best-effort basis; Spawn is solo-maintained.

## Scope

Areas where a report is most useful:

- **Path handling in custom structures**: pasted layouts must not write outside the new project directory (traversal, absolute paths, drive letters, symlinks), and failure cleanup must only remove directories created by the current run.
- **Subprocess calls to `git` and `uv`**: arguments built from user input (project names, extras, dependencies, repository URLs).
- **GitHub publish URL handling**: URL validation, and credentials leaking into error output or git config.

Out of scope: vulnerabilities in third-party packages that generated projects depend on, and issues requiring an attacker who already controls your shell or filesystem.
