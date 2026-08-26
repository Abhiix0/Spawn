## Description

<!-- What does this PR do? Be specific enough that a reviewer can understand the change without reading the diff first. -->

## Related issue

<!-- If this closes an issue: "Closes #N". If there's no issue, delete this section. -->

## Type of change

- [ ] Bug fix
- [ ] New feature / new template
- [ ] Documentation
- [ ] Refactor / internal cleanup
- [ ] CI / tooling

## Checklist

- [ ] `uv run pytest` passes locally
- [ ] `uv run ruff check .` is clean
- [ ] `uv run ruff format --check .` is clean
- [ ] New template PRs include both a `test_<slug>_template.py` and `test_<slug>_generator.py`
- [ ] `tests/test_registry.py` slug count updated (if a template was added or removed)
- [ ] Docs updated if the change affects user-facing behavior (README, docs/, CONTRIBUTING)
