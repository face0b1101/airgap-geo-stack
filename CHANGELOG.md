# Changelog

All notable changes to this Python uv Boilerplate project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- `rename_project.py` now updates all package `__init__.py` files (`src/`, `config/`, `libs/`),
  `tests/__init__.py`, `CHANGELOG.md`, and `version_bump.sh`, fixing post-rename breakages
  caused by missed references (most critically `pkg_version()` in `__init__.py` and the
  hardcoded path in `version_bump.sh`).
- `rename_project.py` renames `tests/test_my_app.py` to `tests/test_<new_name>.py` to match
  the new package name.
- `rename_project.py` handles `docker-build.sh` and `docker-compose.yml` via the same
  regex-based updater as other files, eliminating the YAML round-trip that stripped comments
  and reformatted the compose file. The `pyyaml` dependency is no longer required.
- `rename_project.py` removes itself on successful completion, as it is a one-time setup tool.
  The deletion is guarded by an explicit `success` flag so partial failures leave the script
  intact for re-running.

## [0.3.0] - 2026-01-05

### Added
- Committed `.env.example` template containing the default `LOG_LEVEL` and `TZ` expected by `config/env.py`, plus README guidance on copying it into `.env`.

### Changed
- `src/python_uv_boilerplate/__init__.py` now sources `__version__` from `importlib.metadata` so the package metadata defined in `pyproject.toml` remains the single authority.
- Default timezone falls back to `UTC`, matching the new environment example and logging behaviour.
- `rename_project.py` explicitly updates `pyproject.toml` with its dedicated helper and documents all touched files to make AI tooling safer to run.

## [0.2.0] - 2024-10-03

### Added
- Convenience rename script (`rename_project.py`) for easy project customization
  - Renames the main package directory
  - Updates references in all relevant files (Python files, README.md, pyproject.toml, etc.)
  - Updates Docker-related files (docker-compose.yml, docker-build.sh)
  - Handles both snake_case and kebab-case conventions

## [0.1.0] - 2024-09-30

### Added
- Initial project structure using Python uv
- Basic `pyproject.toml` configuration for uv
- README.md with project description and setup instructions
- This CHANGELOG.md file
- `.gitignore` file tailored for Python projects
- Sample `src/` directory structure
- Basic test setup with pytest
- Environment variable handling with python-dotenv
- Pre-commit hooks configuration
- GitHub Actions workflow for CI/CD

### Changed
- Replaced Poetry dependency management with uv

## [0.0.1] - 2024-09-29

### Added
- Created initial repository
- Added LICENSE file

[Unreleased]: https://github.com/username/python-uv-boilerplate/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/username/python-uv-boilerplate/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/username/python-uv-boilerplate/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/username/python-uv-boilerplate/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/username/python-uv-boilerplate/releases/tag/v0.0.1
