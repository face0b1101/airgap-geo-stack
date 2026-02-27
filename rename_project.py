"""A utility script to rename the project and update all related files.

Files affected:
- Source code: src/[name]/__init__.py, main.py, config/__init__.py, libs/__init__.py
- Config: pyproject.toml, docker-compose.yml, docker-build.sh
- Documentation: README.md (template sections stripped; project skeleton left)
- Tests: tests/__init__.py, tests/test_my_app.py (renamed to test_[name].py)
- Notebooks: notebooks/test.ipynb
- Environment: .env.example copied to .env
- Versioning: CHANGELOG.md, version_bump.sh

The script will prompt for a new project name and handle the renaming process,
maintaining appropriate naming conventions across different file types.
On successful completion the script removes itself, as it is a one-time setup tool.
"""

import json
import os
import re
import shutil
import sys


def prompt_for_project_name() -> str:
    """Prompt the user for a new project name and validate the input.

    Returns:
        str: A valid project name containing only letters, numbers, spaces, or hyphens.

    Raises:
        KeyboardInterrupt: If the user interrupts the input process.
    """
    while True:
        try:
            name = input("Enter the new project name: ").strip()
            if re.match(r"^[a-zA-Z0-9\s-]+$", name):
                return name.lower()

            # else...
            print("Invalid name. Please use only letters, numbers, spaces, or hyphens.")

        except KeyboardInterrupt:
            print("\nProject renaming cancelled.")
            raise


def get_formatted_name(name: str, separator: str) -> str:
    """Format the given name by replacing spaces and hyphens with the specified separator.

    Args:
        name (str): The original name.
        separator (str): The character to use as a separator ('_' or '-').

    Returns:
        str: The formatted name.
    """
    return re.sub(r"[\s-]+", separator, name)


def rename_project(old_name: str, new_name: str) -> None:
    """Rename the project directory and update all references.

    Args:
        old_name (str): The current project name.
        new_name (str): The new project name.

    Raises:
        OSError: If there's an issue with file or directory operations.
    """
    python_new_name = get_formatted_name(new_name, "_")
    kebab_new_name = get_formatted_name(new_name, "-")

    try:
        # Rename the main package directory
        old_path = os.path.join("src", old_name)
        new_path = os.path.join("src", python_new_name)
        os.rename(old_path, new_path)
        print(f"Renamed directory: {old_path} -> {new_path}")

        # Copy .env.example to .env, preserving the original for the repository
        env_example_path = ".env.example"
        env_path = ".env"
        if os.path.exists(env_example_path):
            shutil.copy2(env_example_path, env_path)
            print(f"Copied {env_example_path} -> {env_path}")
        else:
            print(f"Warning: {env_example_path} not found. .env file not created.")

        # List of files to update
        files_to_update = [
            os.path.join("src", python_new_name, "__init__.py"),
            os.path.join("src", python_new_name, "main.py"),
            os.path.join("src", python_new_name, "config", "__init__.py"),
            os.path.join("src", python_new_name, "libs", "__init__.py"),
            "README.md",
            os.path.join("tests", "__init__.py"),
            os.path.join("tests", "test_my_app.py"),
            "CHANGELOG.md",
            "version_bump.sh",
            "docker-build.sh",
            "docker-compose.yml",
        ]

        # Update references in each file
        for file_path in files_to_update:
            if os.path.exists(file_path):
                update_file_content(
                    file_path, old_name, python_new_name, kebab_new_name
                )

        # Strip template-specific sections from README.md
        readme_path = "README.md"
        if os.path.exists(readme_path):
            strip_readme_template_content(readme_path, python_new_name)

        # Rename the test file to match the new project name
        old_test = os.path.join("tests", "test_my_app.py")
        new_test = os.path.join("tests", f"test_{python_new_name}.py")
        if os.path.exists(old_test):
            os.rename(old_test, new_test)
            print(f"Renamed test file: {old_test} -> {new_test}")

        # Update pyproject separately to cover scripts and metadata
        pyproject_path = "pyproject.toml"
        if os.path.exists(pyproject_path):
            update_pyproject_toml(
                pyproject_path, old_name, python_new_name, kebab_new_name
            )
        else:
            print(f"Warning: {pyproject_path} not found. Project metadata not updated.")

        # Update Jupyter notebook
        notebook_path = os.path.join("notebooks", "test.ipynb")
        if os.path.exists(notebook_path):
            update_notebook(notebook_path, old_name, python_new_name)

    except OSError as e:
        print(f"An error occurred while renaming the project: {e}")
        raise


def update_pyproject_toml(
    file_path: str, old_name: str, python_new_name: str, kebab_new_name: str
) -> None:
    """Update the pyproject.toml file, replacing the old project name with the new name in appropriate formats.

    Args:
        file_path (str): Path to the pyproject.toml file.
        old_name (str): The current project name.
        python_new_name (str): The new project name in Python-friendly format.
        kebab_new_name (str): The new project name in kebab-case format.

    Raises:
        OSError: If there's an issue reading from or writing to the file.
    """
    try:
        with open(file_path) as file:
            content = file.read()

        # Replace kebab-case project name
        content = re.sub(
            r"\b" + re.escape(old_name.replace("_", "-")) + r"\b",
            kebab_new_name,
            content,
        )

        # Replace Python-style project name
        content = re.sub(r"\b" + re.escape(old_name) + r"\b", python_new_name, content)

        with open(file_path, "w") as file:
            file.write(content)
        print(f"Updated pyproject.toml: {file_path}")

    except OSError as e:
        print(f"An error occurred while updating {file_path}: {e}")
        raise


def update_file_content(
    file_path: str, old_name: str, python_new_name: str, kebab_new_name: str
) -> None:
    """Update the content of a file, replacing old project name references while preserving case conventions.

    Args:
        file_path (str): Path to the file to update.
        old_name (str): The current project name.
        python_new_name (str): The new project name in Python-friendly format (snake_case).
        kebab_new_name (str): The new project name in kebab-case format.

    Raises:
        OSError: If there's an issue reading from or writing to the file.
    """
    try:
        with open(file_path) as file:
            content = file.read()

        # Create old name variations
        old_kebab = old_name.replace("_", "-")
        old_python = old_name.replace("-", "_")

        # Function to replace while preserving case convention
        def replace_preserving_convention(match):
            if "-" in match.group(0):
                return kebab_new_name
            else:
                return python_new_name

        # Replace old name with new name, preserving convention
        updated_content = re.sub(
            r"\b" + re.escape(old_kebab) + r"\b|\b" + re.escape(old_python) + r"\b",
            replace_preserving_convention,
            content,
        )

        # Special handling for README.md heading
        if file_path.lower().endswith("readme.md"):
            updated_content = re.sub(
                r"(#\s*Python\s+)`uv`(\s*Boilerplate)",
                f"\\1`{kebab_new_name}`\\2",
                updated_content,
            )

        # Update Python imports
        updated_content = re.sub(
            r"from\s+" + re.escape(old_python) + r"([\.\s])",
            f"from {python_new_name}\\1",
            updated_content,
        )
        updated_content = re.sub(
            r"import\s+" + re.escape(old_python) + r"\b",
            f"import {python_new_name}",
            updated_content,
        )

        with open(file_path, "w") as file:
            file.write(updated_content)
        print(f"Updated references in: {file_path}")

    except OSError as e:
        print(f"An error occurred while updating {file_path}: {e}")
        raise


def strip_readme_template_content(file_path: str, python_new_name: str) -> None:
    """Remove template-specific sections from README.md, leaving a project skeleton.

    Removes the 'How to Create a new Project' section (including Housekeeping),
    the ONBOARDING.md AI-assistant bullet, and the rename_project.py folder entry.
    Replaces the template description line with a TODO placeholder and updates the
    test file name in the folder structure diagram.

    Args:
        file_path (str): Path to the README.md file.
        python_new_name (str): New project name in snake_case, used to update the
            folder structure diagram.

    Raises:
        OSError: If there's an issue reading from or writing to the file.
    """
    try:
        with open(file_path) as file:
            content = file.read()

        # Replace the template description with a placeholder
        content = re.sub(
            r"Template for creating basic python projects using \[uv\]\([^)]+\)",
            "TODO: Add a short project description.",
            content,
        )

        # Remove the entire "How to Create a new Project" section (incl. Housekeeping)
        content = re.sub(
            r"\n## How to Create a new Project\n.*?(?=\n## How to Code)",
            "",
            content,
            flags=re.DOTALL,
        )

        # Remove the ONBOARDING.md bullet from the AI assistants section
        content = re.sub(
            r"- When a new project is created from this template[^\n]*\n",
            "",
            content,
        )

        # Remove rename_project.py from the folder structure (script self-deletes)
        content = re.sub(r"[^\n]*rename_project\.py[^\n]*\n", "", content)

        # Update test file name in the folder structure diagram
        content = content.replace("test_my_app.py", f"test_{python_new_name}.py")

        with open(file_path, "w") as file:
            file.write(content)
        print(f"Stripped template content from: {file_path}")

    except OSError as e:
        print(
            f"An error occurred while stripping template content from {file_path}: {e}"
        )
        raise


def update_notebook(notebook_path: str, old_name: str, new_name: str) -> None:
    """Update references in a Jupyter notebook, replacing the old project name with the new one.

    Args:
        notebook_path (str): Path to the notebook file.
        old_name (str): The current project name.
        new_name (str): The new project name in Python-friendly format.

    Raises:
        OSError: If there's an issue reading from or writing to the notebook file.
        json.JSONDecodeError: If the notebook file is not valid JSON.
    """
    try:
        with open(notebook_path, encoding="utf-8") as file:
            notebook = json.load(file)

        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                cell["source"] = [
                    line.replace(old_name, new_name) for line in cell["source"]
                ]

        with open(notebook_path, "w", encoding="utf-8") as file:
            json.dump(notebook, file, indent=1)
        print(f"Updated references in notebook: {notebook_path}")

    except OSError as e:
        print(f"An error occurred while updating the notebook {notebook_path}: {e}")
        raise

    except json.JSONDecodeError as e:
        print(f"The notebook file {notebook_path} is not valid JSON: {e}")
        raise


def main() -> None:
    """Main function to execute the project renaming process.

    On success the script removes itself, as it is a one-time setup tool.

    Raises:
        Exception: If an unexpected error occurs during the renaming process.
    """
    old_name = "python_uv_boilerplate"
    success = False

    try:
        new_name = prompt_for_project_name()
        print(f"Renaming project from '{old_name}' to '{new_name}'")
        rename_project(old_name, new_name)
        success = True
        print("Project renamed successfully.")
        print("Run `uv sync` to refresh the lock file with the new package name.")

    except KeyboardInterrupt:
        print("\nProject renaming cancelled.")
        sys.exit(0)  # Exit with status code 0 for a "successful" termination

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)  # Exit with status code 1 to indicate an error occurred

    if success:
        script_path = os.path.abspath(__file__)
        os.remove(script_path)
        print(f"Removed setup script: {script_path}")


if __name__ == "__main__":
    main()
