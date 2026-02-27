#!/bin/bash

# Ensure we're in the root of the git repository
if [ ! -d .git ]; then
    echo "Error: This script must be run from the root of the git repository."
    exit 1
fi

# Get the new version number
read -p "Enter the new version number (e.g., 0.2.0): " NEW_VERSION

# Update pyproject.toml
sed -i '' "s/^version = .*/version = \"$NEW_VERSION\"/" pyproject.toml

# Update __init__.py
# Note: This assumes the version is on a line starting with '__version__'
sed -i '' "s/^__version__ = .*/__version__ = \"$NEW_VERSION\"/" src/python_uv_boilerplate/__init__.py

# Commit the changes
git add pyproject.toml CHANGELOG.md src/python_uv_boilerplate/__init__.py
git commit -m "Bump version to $NEW_VERSION"

# Create a new tag
git tag -a v$NEW_VERSION -m "Release version $NEW_VERSION"

# Push changes and tags
git push origin main
git push origin v$NEW_VERSION

echo "Version bumped to $NEW_VERSION and pushed to GitHub."
echo "Don't forget to create a release on GitHub!"
