<div align="center">

# Spawn

> Your next project is one command away.

[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![uv](https://img.shields.io/badge/Powered%20by-uv-orange?style=flat-square)](https://github.com/astral-sh/uv)

![Spawn Preview](assets/preview.png)

</div>

---

Every Python project starts the same way — not with code, but with setup.

Directories. Git. A virtual environment. A `.gitignore`. Commands you've typed a hundred times that have nothing to do with what you're actually trying to build.

**Spawn eliminates that entirely.**

One command. An interactive prompt. A fully structured project waiting for you on the other side — with Git initialized, a virtual environment ready, and the exact next steps printed so you never have to guess.

```bash
spawn create
```

That's it. You pick the template. Spawn handles the rest.

---

## Who It's For

- **New to Python?** Stop spending your first hour on setup. Start writing code.
- **Seasoned dev?** You know how tedious this is. You don't have to do it anymore.
- **Building something serious?** Spawn's structure keeps your projects consistent from day one.

---

## But What About After Setup?

Most tools stop once the scaffolding is done. Spawn doesn't.

```bash
spawn doctor
```

Run it inside any project — not just ones Spawn created. It scans for the things that actually matter: documentation, version control, test configuration, linting, deployment setup, and more. Everything gets scored.

You'll know exactly where your project stands and what it's missing — without digging through folders yourself.

---

## Get Started

**Prerequisites:** Python 3.12+, [uv](https://github.com/astral-sh/uv), Git

```bash
git clone https://github.com/Abhiix0/Spawn.git
cd Spawn
uv sync
uv tool install .
```

Run `spawn create` — the rest explains itself.

Want to verify everything works after cloning? Run:

```bash
uv run pytest
```

If something breaks, [open an issue](https://github.com/Abhiix0/Spawn/issues).

---

## Under the Hood *(kind of)*

Spawn isn't magic. It's just everything you'd do manually, done right, done fast, done consistently — powered by [uv](https://github.com/astral-sh/uv) and built to stay out of your way.

4 templates. Each one opinionated enough to be useful, flexible enough to make your own.

---

## What's Coming

A few things already in progress — GitHub publishing, Docker support, a template marketplace, config file support, and more. The full roadmap is in the repo.

Every great tool gets better with the people who use it. If something bugs you, something's missing, or you have an idea — you're in the right place. Here's how adding a new template works:

1. **Create the template** in `src/spawn/templates/your_template.py`.
   Subclass `BaseTemplate` and define the folder structure.
2. **Register it** in `src/spawn/core/registry.py`.
   Add your template to the registry so Spawn can find it.
3. **Add next steps** in `src/spawn/utils/next_steps.py`.
   Tell users what to do after the project is created.

Not sure where to start? Check the [open issues](https://github.com/Abhiix0/Spawn/issues).

---

[![MIT License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE) — use it, fork it, build on it.
