# Spawn Doctor

## Overview

`spawn doctor` is a read-only project health checker that analyzes your project directory and reports whether common project standards and best practices are present.

## Purpose

The doctor command helps developers:
- Quickly assess project health and completeness
- Identify missing best practices
- Get actionable recommendations for improvements
- Maintain consistency across projects
- Onboard new contributors by showing expected project structure

## Command Usage

```bash
spawn doctor
```

The command runs in the current directory and produces a comprehensive health report with:
- ✓ Green checkmarks for passing checks
- ⚠ Yellow warnings for missing items
- Overall health score (0-100)
- Prioritized recommendations

### Example Output

```
╭────────────────────────── 🏥 Project Health Report ──────────────────────────╮
│                                                                              │
│  Documentation                                                               │
│    ✓ README.md — Documentation file present                                  │
│    ✓ LICENSE — License file present                                          │
│                                                                              │
│  Version Control                                                             │
│    ✓ Git Repository — Git initialized                                        │
│    ✓ .gitignore — Git ignore configured                                      │
│                                                                              │
│  Quality                                                                     │
│    ✓ Tests — Test directory configured                                       │
│    ✓ Ruff — Ruff configured in pyproject.toml (dependency)                   │
│    ✓ Pytest — Pytest configured in pyproject.toml (dependency)               │
│                                                                              │
│  Deployment                                                                  │
│    ⚠ Dockerfile — Missing Dockerfile                                         │
│    ✓ GitHub Actions — GitHub Actions configured (1 workflow)                 │
│                                                                              │
│  Configuration                                                               │
│    ⚠ .env.example — Missing .env.example                                     │
│                                                                              │
│  Project Score: 85/100 (85%)                                                 │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

╭───────────────────────────── 💡 Recommendations ─────────────────────────────╮
│                                                                              │
│  1. Add a Dockerfile for containerized deployment                            │
│  2. Create a .env.example file to document required environment variables    │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Architecture

### Module Structure

```
src/spawn/
├── cli/
│   └── app.py                 # Command registration
└── utils/
    └── doctor.py              # Health check implementation
```

### Key Components

#### `HealthCheck` (Dataclass)
Represents a single health check result.

**Attributes:**
- `name`: Display name of the check
- `category`: Category this check belongs to
- `passed`: Boolean indicating if check passed
- `message`: Descriptive result message
- `weight`: Numeric weight for scoring (higher = more important)

#### `ProjectHealthChecker` (Class)
Main health checking implementation.

**Methods:**
- Individual check methods for each standard
- `run_all_checks()`: Executes all checks
- `calculate_score()`: Computes weighted score
- `group_checks_by_category()`: Organizes results
- `generate_recommendations()`: Creates prioritized action items
- `format_report()`: Renders Rich console output

#### `run_health_check()` (Function)
Entry point function called by the CLI command.

## Health Checks

The doctor performs 10 checks across 5 categories:

### Documentation (2 checks)
- **README.md** (Weight: 10) - Project documentation file
- **LICENSE** (Weight: 5) - License terms file

### Version Control (2 checks)
- **Git Repository** (Weight: 15) - `.git` directory present
- **.gitignore** (Weight: 10) - Git ignore configuration

### Quality (3 checks)
- **Tests Directory** (Weight: 15) - `tests/` directory exists
- **Ruff** (Weight: 10) - Linter configured
- **Pytest** (Weight: 10) - Test framework configured

### Deployment (2 checks)
- **Dockerfile** (Weight: 10) - Docker containerization
- **GitHub Actions** (Weight: 10) - CI/CD workflows in `.github/workflows/`

### Configuration (1 check)
- **.env.example** (Weight: 5) - Environment variable template

## Scoring System

### Weighted Scoring
Each check has a weight representing its importance:
- Critical items (Git, Tests): 15 points
- Standard items (README, .gitignore, tools): 10 points
- Optional items (LICENSE, .env.example): 5 points

**Total Possible Score:** 100 points

### Score Interpretation
- **80-100%** (Green): Excellent health
- **50-79%** (Yellow): Good, with room for improvement
- **0-49%** (Red): Needs attention

## Configuration Detection

### Ruff Detection
Checks for Ruff configuration in:
1. `ruff.toml` - Dedicated Ruff config
2. `.ruff.toml` - Hidden Ruff config
3. `pyproject.toml` - `[tool.ruff]` section or `ruff` dependency

### Pytest Detection
Checks for Pytest configuration in:
1. `pytest.ini` - Dedicated pytest config
2. `setup.cfg` - `[pytest]` or `[tool:pytest]` section
3. `pyproject.toml` - `[tool.pytest]` section or `pytest` dependency

### GitHub Actions Detection
Checks for workflow files (`.yml` or `.yaml`) in `.github/workflows/` directory.
Reports the count of configured workflows.

## Recommendations

The doctor generates prioritized recommendations for failed checks:

**Priority Order:**
1. Initialize Git repository
2. Add README.md
3. Create tests directory
4. Add .gitignore
5. Configure Pytest
6. Configure Ruff
7. Set up GitHub Actions
8. Add Dockerfile
9. Add LICENSE
10. Create .env.example

Recommendations are actionable and include specific commands where applicable.

## Extension Guide

### Adding New Checks

To add a new health check:

1. **Create check method in `ProjectHealthChecker`:**
```python
def check_new_item(self) -> HealthCheck:
    """Check if new item exists."""
    item_path = self.project_path / "new_item"
    passed = item_path.exists()
    return HealthCheck(
        name="New Item",
        category="Category Name",
        passed=passed,
        message="Message when passed" if passed else "Message when failed",
        weight=10,  # Adjust weight based on importance
    )
```

2. **Add to `get_all_checks()` method:**
```python
def get_all_checks(self) -> List[Callable[[], HealthCheck]]:
    return [
        # ... existing checks ...
        self.check_new_item,
    ]
```

3. **Add recommendation mapping in `generate_recommendations()`:**
```python
priority_map = {
    # ... existing mappings ...
    "New Item": (
        "Actionable recommendation text",
        11,  # Priority number (lower = higher priority)
    ),
}
```

4. **Write tests in `tests/test_doctor.py`:**
```python
def test_check_new_item_exists(self, temp_project_dir):
    """Test new item check when item exists."""
    (temp_project_dir / "new_item").touch()
    checker = ProjectHealthChecker(temp_project_dir)
    result = checker.check_new_item()
    
    assert result.passed is True

def test_check_new_item_missing(self, temp_project_dir):
    """Test new item check when item is missing."""
    checker = ProjectHealthChecker(temp_project_dir)
    result = checker.check_new_item()
    
    assert result.passed is False
```

### Adding New Categories

To add a new category, simply use the new category name in your check's `category` attribute. The `group_checks_by_category()` method automatically handles new categories.

To control display order, update the `category_order` list in `format_report()`:

```python
category_order = [
    "Documentation",
    "Version Control",
    "Quality",
    "Deployment",
    "Configuration",
    "Your New Category",  # Add here
]
```

## Testing

### Test Coverage
The implementation includes comprehensive unit tests covering:
- Individual check methods (exists/missing scenarios)
- Scoring calculations
- Category grouping
- Recommendation generation
- Integration tests on various project states
- Edge cases (empty projects, complete projects, partial projects)

### Running Tests
```bash
pytest tests/test_doctor.py -v
```

### Test Scenarios
1. **Complete Project** - All checks pass (100/100)
2. **Minimal Project** - Only README + Git (25/100)
3. **Partial Project** - Common items present (55/100)
4. **Empty Project** - No checks pass (0/100)

## Implementation Notes

### Read-Only Design
The doctor command **never modifies** any files or directories. It only:
- Reads file/directory existence
- Reads file contents for configuration detection
- Outputs analysis results

### Error Handling
- File read errors are caught and treated as "not configured"
- Missing directories are handled gracefully
- Invalid paths default to current directory

### Performance
- All checks are lightweight (file existence or simple content checks)
- No external API calls
- Typically completes in <100ms

### Compatibility
- Works on any directory (not just Python projects)
- Configurable project path for flexibility
- Platform-independent (Windows, macOS, Linux)

## Future Enhancements

Potential improvements for future versions:
- Custom check profiles (web, CLI, library, etc.)
- Configurable weights via config file
- Export reports to JSON/HTML
- Integration with CI/CD pipelines
- Check for code coverage thresholds
- Dependency vulnerability scanning
- Security best practices checks
- Performance benchmark checks
