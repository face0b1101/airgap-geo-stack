# Project Onboarding

> **AI agents:** follow this guide to configure a new project from the `python-uv-boilerplate` template.
> **Human users:** follow the [Housekeeping](../README.md#housekeeping) section in `README.md` instead.

______________________________________________________________________

## Before You Start

This project was created from the
[python-uv-boilerplate](https://github.com/face0b1101/python-uv-boilerplate) template.
The steps below replace every reference to `python-uv-boilerplate` with the real project
identity and prepare the repository for active development.

Work through each step in order. Do not skip ahead - later steps depend on the rename
having been completed.

______________________________________________________________________

## Step 1 - Gather Project Information

Ask the user to confirm the following details before making any changes. Record the
answers; you will use them in every subsequent step.

| Field | Description | Example |
|---|---|---|
| **Project name** | Kebab-case identifier used in package names, Docker images, and git history | `my-cool-project` |
| **Short description** | One sentence that describes what the project does | `Processes widget data from the Acme API` |
| **Project goal** | What problem does this project solve, or what outcome is expected? | `Automate nightly reconciliation of widget inventory` |
| **Author name** | Full name of the primary maintainer | `Jane Smith` |
| **Author e-mail** | Contact e-mail for `pyproject.toml` | `jane@example.com` |

> If the user cannot supply all fields right away, collect what is available and leave
> placeholder comments in the affected files so nothing is silently wrong.

______________________________________________________________________

## Step 2 - Run the Rename Script

The rename script rewrites package names, imports, config files, Docker assets, and the
notebook in one pass. It reads the project name from `stdin`, so it can be driven
non-interactively:

```bash
echo "<project-name>" | uv run rename_project.py
```

Replace `<project-name>` with the kebab-case name from Step 1 (e.g. `my-cool-project`).

The script touches the following files - verify each one was updated cleanly:

| File | What changes |
|---|---|
| `src/python_uv_boilerplate/` | Directory renamed to `src/<project_name>/` |
| `.env.example` | Copied to `.env` |
| `src/<project_name>/main.py` | Import paths updated |
| `pyproject.toml` | `name` field and script entry point updated |
| `README.md` | Heading and name references updated |
| `tests/test_my_app.py` | Import paths updated |
| `notebooks/test.ipynb` | Import paths updated |
| `docker-build.sh` | `DEFAULT_PROJECT_NAME` updated |
| `docker-compose.yml` | Image and container names updated |

______________________________________________________________________

## Step 3 - Update Metadata the Script Does Not Touch

The rename script updates names and imports, but not project-specific descriptions or
author details. Edit the following manually.

### `pyproject.toml`

- `description` → replace the boilerplate description with the **short description** from Step 1
- `authors` → set `name` and `email` to the **author details** from Step 1
- `maintainers` → same as `authors` unless otherwise specified

```toml
[project]
description = "<short description>"
authors = [{ name = "<author name>", email = "<author email>" }]
maintainers = [{ name = "<author name>", email = "<author email>" }]
```

### `README.md`

- Replace the opening paragraph (`Template for creating basic python projects using uv`)
  with a project-specific introduction covering the **goal** from Step 1.
- Update the folder-structure block if the `docs/` directory or other paths differ from
  the template defaults.

### `CHANGELOG.md`

- Replace the placeholder `[Unreleased]` entry with the first real entry for this
  project, using today's date and a brief note about the initial setup.

```markdown
## [Unreleased]

## [0.1.0] - YYYY-MM-DD

### Added
- Initial project created from python-uv-boilerplate template
- <any additional notes>
```

- Remove historical boilerplate changelog entries (`[0.3.0]`, `[0.2.0]`, etc.) - they
  belong to the template, not this project.
- Update the comparison links at the bottom to point to the correct repository URL.

______________________________________________________________________

## Step 4 - Sync Dependencies and Verify

```bash
uv sync
make test
```

All tests must pass before proceeding. If any fail, diagnose and fix before moving on.

______________________________________________________________________

## Step 5 - Optional: Enable Pre-commit Hooks

```bash
uv run pre-commit install
uv run pre-commit autoupdate --repo https://github.com/pre-commit/pre-commit-hooks
```

______________________________________________________________________

## Step 6 - Commit the Setup

Stage all changes and create the initial setup commit:

```bash
git add -A
git commit -m "chore: initialise project from python-uv-boilerplate template"
```

> If you created a fresh repository (not a template clone), also set the remote and push:
>
> ```bash
> git remote add origin https://github.com/<org>/<project-name>.git
> git push -u origin main
> ```

______________________________________________________________________

## Checklist

Use this as a final sanity check before handing back to the user.

- [ ] Project name confirmed with user
- [ ] `uv run rename_project.py` ran without errors
- [ ] `pyproject.toml`: `description`, `authors`, `maintainers` updated
- [ ] `README.md`: opening paragraph reflects actual project goal
- [ ] `CHANGELOG.md`: boilerplate entries removed; first real entry added
- [ ] `uv sync` completed without errors
- [ ] `make test` - all tests pass
- [ ] Pre-commit hooks installed (if required by the user)
- [ ] Initial commit created
