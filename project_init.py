#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import getpass

# Base directory (current working directory)
BASE = Path.cwd()

# Directories to create
DIRS = [
    BASE / "app",
    BASE / "app" / "routers",
    BASE / "app" / "database",
    BASE / "app" / "schemas",
    BASE / "app" / "models",
    BASE / "app" / "external_services",
    BASE / "app" / "utils",
    BASE / "tests",
]

# Files to create with their initial content
FILES = {
    # app root
    BASE / "app" / "__init__.py": "# this file makes \"app\" a Python package.\n",
    BASE / "app" / "main.py": "# Initializes the FastAPI application.\n",
    BASE / "app" / "dependencies.py": "# Defines dependencies used by the routers.\n",

    # routers
    BASE / "app" / "routers" / "__init__.py": "",
    BASE / "app" / "routers" / "items.py": "# Defines routes and endpoints related to items.\n",
    BASE / "app" / "routers" / "users.py": "# Defines routes and endpoints related to users.\n",

    # database
    BASE / "app" / "database" / "__init__.py": "",
    BASE / "app" / "database" / "db.py": "# Defines database operations for db.\n",
    BASE / "app" / "database" / "user.py": "# Defines database operations for users.\n",

    # schemas
    BASE / "app" / "schemas" / "__init__.py": "",
    BASE / "app" / "schemas" / "pdfschema.py": "# Defines schemas for pdfschema.\n",
    BASE / "app" / "schemas" / "user.py": "# Defines schemas for users.\n",

    # models
    BASE / "app" / "models" / "__init__.py": "",
    BASE / "app" / "models" / "pdfModel.py": "# Defines database models for pdfModel.\n",
    BASE / "app" / "models" / "user.py": "# Defines database models for users.\n",

    # external_services
    BASE / "app" / "external_services" / "__init__.py": "",
    BASE / "app" / "external_services" / "email.py": "# Defines functions for sending emails.\n",
    BASE / "app" / "external_services" / "notification.py": "# Defines functions for sending notifications.\n",

    # utils
    BASE / "app" / "utils" / "__init__.py": "",
    BASE / "app" / "utils" / "authentication.py": "# Defines functions for authentication.\n",
    BASE / "app" / "utils" / "validation.py": "# Defines functions for validation.\n",

    # tests
    BASE / "tests" / "__init__.py": "",
    BASE / "tests" / "test_main.py": "# Tests for the main app module.\n",
    BASE / "tests" / "test_items.py": "# Tests for the items module.\n",
    BASE / "tests" / "test_users.py": "# Tests for the users module.\n",

    # project root
    BASE / "requirements.txt": "",
    BASE / ".gitignore": "# add files/directories to ignore\n",
    BASE / "README.md": "# Project Title\n\nA short description of your project.\n",
}

def scaffold():
    # Create directories
    for d in DIRS:
        d.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {d.relative_to(BASE)}")

    # Create files
    for path, content in FILES.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            print(f"Created file: {path.relative_to(BASE)}")
        else:
            print(f"Skipped (already exists): {path.relative_to(BASE)}")

def init_git_and_set_credentials():
    print("\n⎯⎯⎯ Initializing Git and configuring local credentials ⎯⎯⎯\n")

    # 1. git init
    subprocess.run(["git", "init"], check=True)
    print("Initialized empty Git repository.")

    # 2. set user.name and user.email
    name = input("Enter Git user.name: ").strip()
    email = input("Enter Git user.email: ").strip()
    subprocess.run(["git", "config", "user.name", name], check=True)
    subprocess.run(["git", "config", "user.email", email], check=True)
    print(f"Set local user.name = {name!r} and user.email = {email!r}")

    # 3. configure credential helper to store in project .git-credentials
    subprocess.run([
        "git", "config", "credential.helper",
        "store --file " + str(BASE / ".git-credentials")
    ], check=True)
    print("Configured Git to store credentials in .git-credentials")

    # 4. prompt for host and password, then approve via git credential
    host = input("Enter Git host (e.g. github.com): ").strip()
    pwd = getpass.getpass(f"Enter password for {name} at {host}: ")
    cred_data = (
        f"protocol=https\n"
        f"host={host}\n"
        f"username={name}\n"
        f"password={pwd}\n\n"
    ).encode()

    p = subprocess.Popen(
        ["git", "credential", "approve"],
        stdin=subprocess.PIPE
    )
    p.communicate(cred_data)
    print("Stored your credentials in .git-credentials (in plaintext).")

def main():
    scaffold()
    init_git_and_set_credentials()
    print("\n✅ All done! Your project is scaffolded and Git is configured locally.")

if __name__ == "__main__":
    main()
