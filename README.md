# Python `uv` Boilerplate

Template for creating basic python projects using [uv](https://github.com/astral-sh/uv)

## Folder Structure

```sh
python-uv-boilerplate
├── .github/
│   └── workflows/
│       └── ci.yaml           # GitHub Actions pipeline (lint + test)
├── docs/
│   └── ONBOARDING.md         # Setup guide for AI agents and human users
├── notebooks/
│   └── test.ipynb            # Example notebook (imports renamed by script)
├── src/
│   └── python_uv_boilerplate # Main package (rename via rename_project.py)
│       ├── config/
│       │   └── env.py        # Environment variable helpers
│       ├── libs/
│       │   └── my_lib.py     # Sample reusable module
│       ├── __init__.py       # Exposes package metadata
│       └── main.py           # Entry point with logging demo
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   └── test_my_app.py        # Sample coverage (hello + rename helper)
├── .env.example              # Copy to .env and customise
├── AGENTS.md                 # Quick rules for coding agents
├── CHANGELOG.md              # Release notes
├── dockerfile                # Multi-stage build image definition
├── docker-build.sh           # Helper for manual Docker builds
├── docker-compose.yml        # Compose service definition
├── Makefile                  # Standardised automation targets
├── pyproject.toml            # Project + tooling configuration
├── README.md                 # You are here
├── rename_project.py         # Automated rename/housekeeping script
├── uv.lock                   # Locked dependency graph
└── version_bump.sh           # Simple release helper script
```

## How to Create a new Project

There are two ways to create a new Project.

### 1. Create a new Project from the repo as a template

Pretty straightforward. Go to the [repository](https://github.com/face0b1101/python-uv-boilerplate) and click the green `Use this template` button.

See [here](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) for more details.

### 2. Create a Fork

Alternatively, create a fork the _old-fashioned_ way:

- Create new repository on GitHub (`new-repository-name`)
- Create another folder on local machine
- Bare clone this repository

    ```bash
    git clone --bare https://github.com/face0b1101/python-uv-boilerplate
    ```

- CD to this folder (with .git suffix) and push mirror to GitHub

    ```bash
    cd python-uv-boilerplate.git
    git push --mirror https://github.com/face0b1101/new-repository-name.git
    ```

- Remove `python-uv-boilerplate.git` folder from local folder
- Clone `new-repository-name` to local folder

### Housekeeping

When you have your new project set up, a bit of housekeeping is required:

1. Make sure you have [uv installed](https://docs.astral.sh/uv/getting-started/installation/)

2. Ensure python version is set

    ```bash
    uv python pin 3.12
    ```

3. Create a Python Virtual Environment for the project

    ```bash
    uv venv
    uv sync
    ```

4. Configure environment variables

    ```bash
    cp .env.example .env
    ```

    Update `LOG_LEVEL` and `TZ` (defaults: `INFO` / `UTC`) to match your deployment environment. The rename script in the next step also performs this copy automatically.

5. Rename the project - there is a convenience script, `rename_project.py`

    ```bash
    uv run rename_project.py
    ```

    The script performs the following actions:

    - Rename `src/python_uv_boilerplate` directory to `src/new_project_name`
    - Rename `.env.example` to `.env`
    - Rename `tests/test_my_app.py` to `tests/test_new_project_name.py`
    - Update project name references across all relevant files:
      - `src/new_project_name/__init__.py`, `main.py`, `config/__init__.py`, `libs/__init__.py`
      - `tests/__init__.py`, `tests/test_new_project_name.py`
      - `pyproject.toml`, `README.md`, `CHANGELOG.md`, `version_bump.sh`
      - `docker-build.sh`, `docker-compose.yml`
    - Update imports in `notebooks/test.ipynb`
    - Deletes itself on successful completion

6. Reset the changelog

   Replace `CHANGELOG.md` with a clean slate for your project. Remove the boilerplate
   history entries and add an initial entry:

   ```markdown
   ## [Unreleased]

   ## [0.1.0] - YYYY-MM-DD

   ### Added
   - Initial project created from python-uv-boilerplate template
   ```

   Update the comparison links at the bottom of the file to point to your repository URL.

7. Update the venv

    ```bash
    uv sync
    ```

8. Run pytest to ensure that renames have been successful

    ```bash
    uv run pytest
    ```

    If the tests run without error then you have configured your project and you're ready to get coding.

9. Enable git pre-commit hooks - _optional_

   Some example pre-commit hooks are configured in `.pre-commit-config.yaml`. These can be enabled by running:

   ```bash
   uv run pre-commit install
   ```

   might be worth updating hooks, too:

   ```bash
   uv run pre-commit autoupdate --repo https://github.com/pre-commit/pre-commit-hooks
   ```

## How to Code

1. Create a new branch

   ```bash
   git branch <new-branch>
   ```

2. Do some coding and stuff...

3. Push the new branch and changes

   ```bash
   git push -u origin <new-branch>
   ```

## How to Commit

- Commit on the branch
- PR if it should be merged
- Specify the type of commit:
  - feat: The new feature you're adding to a particular application
  - fix: A bug fix
  - style: Feature and updates related to styling
  - refactor: Refactoring a specific section of the codebase
  - test: Everything related to testing
  - docs: Everything related to documentation
  - chore: Regular code maintenance.[ You can also use emojis to represent commit types]

## Automation

Common tasks are wrapped in the project `Makefile`:

- `make install` – install/refresh dependencies with uv
- `make lint` / `make format` – run Ruff in check or format mode
- `make test` – execute the pytest suite
- `make precommit` – run all configured pre-commit hooks
- `make run` – invoke the sample `hello` entry point

GitHub Actions executes `make install`, `make lint`, and `make test` on every push/PR via [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml).

## Working with AI Coding Assistants

- Follow the plan/approval workflow: request approval before editing and summarise changes plus tests before handing back.
- Use the Makefile targets above for deterministic commands (`make lint`, `make test`, etc.) so local runs match CI.
- Keep replies factual, stick to UK-English spelling, and capture assumptions up front.
- When a new project is created from this template, follow [`docs/ONBOARDING.md`](docs/ONBOARDING.md) to rename the project, update metadata, and verify the setup. AI agents should follow that guide directly; human users can follow the [Housekeeping](#housekeeping) section above.
- Snapshot context succinctly in final updates: mention touched files, risks, and outstanding work.

## Docker

You can also build and run your app using [Docker](https://docs.docker.com/get-docker/).

## Building the container

First, build the docker container. There is a Dockerfile in the root of the repository. There is a convenience script, `docker-build.sh`, or you can use `docker` or `docker-compose`:

```sh
# docker
DOCKER_BUILDKIT=1 docker build -f Dockerfile --target runtime -t python-uv-boilerplate:0.1 .

# docker-compose
docker-compose build
```

Once the container is built, you can run it with:

```shell
# docker
docker run --rm --name my-container --env-file .env python-uv-boilerplate:0.1

# docker-compose
docker-compose up
```

## Jupyter

If you're working within a project, you can start a Jupyter server with access to the project's virtual environment via the following:

```bash
uv run --with jupyter jupyter lab
```

By default, jupyter lab will start the server at <http://localhost:8888/lab>.
