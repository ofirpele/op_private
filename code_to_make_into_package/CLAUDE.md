# Project Configuration

## Python Environment
- This project uses `uv` for dependency management
- Python version is specified in `.python-version` file
- Always use `uv run` to execute Python commands
- Use `uv add` for new dependencies

## Code Quality
- Before finishing always run:
  - `op_test`

## Testing
- Testing framework: `pytest`
- **Run all tests**: `op_test` (auto-formats with ruff, checks with ruff, then runs pytest)
- **Run tests verbose**: `op_test_verbose` (runs with -vv flag)
- **Run with coverage**: `op_test_coverage` (shows total coverage percentage)
- **Run with verbose coverage**: `op_test_coverage_verbose` (shows missing lines)
- **Run specific test file**: `uv run pytest path/to/_test__file.py`
- **Run specific test**: `uv run pytest path/to/_test__file.py::test_function_name`
- Always write tests for new features and bug fixes
- Test files should be named `_test__*.py` (NOT `test_*.py` or `*_test.py`)
- Test functions should be named `test_*`

## Workflow Preferences
- After making code changes:
  1. Format with ruff
  2. Check with ruff
  3. Run relevant tests
  4. Ensure all tests pass before considering the task complete

## Git & Version Control
🚫 **NEVER USE GIT COMMANDS** 🚫
- Do not run any git commands (git add, git commit, git push, git branch, etc.)
- Do not create commits
- Do not create branches
- Do not suggest git workflows
- I will handle ALL version control manually
- Only focus on writing and modifying code

## Code Style Preferences

### General
- Abstract methods should use `pass` instead of `...`
- **Never use `noqa` comments** to suppress linter warnings unless explicitly asked
  - Fix the underlying issue instead (e.g., move imports to top of file)

### Docstrings
- **Omit docstrings** 
- Use docstrings only if I explicitly ask you

### Test Code Style
- **Use descriptive variable names** that clearly indicate what is being tested
  - Good: `test_blackbox_against_naive_implementation` ()
  - Bad: `test_distance`, `a1`
- **Rename generic test variables** to be more specific about what they test
  - Good: `overlapping_timeperiod_with_period1`
  - Bad: `overlapping_timeperiod`