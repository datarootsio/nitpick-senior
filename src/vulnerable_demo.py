"""Demo file with intentional vulnerabilities for semgrep showcase.

WARNING: This file contains intentionally vulnerable code for testing purposes.
DO NOT use any of these patterns in production code.
"""

import os
import pickle
import subprocess
import sqlite3


def sql_injection_example(user_input: str) -> list:
    """Vulnerable to SQL injection - user input directly in query."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    # BAD: Direct string formatting with user input
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    cursor.execute(query)
    return cursor.fetchall()


def command_injection_example(filename: str) -> str:
    """Vulnerable to command injection via shell=True."""
    # BAD: User input passed to shell command
    result = subprocess.run(
        f"cat {filename}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def hardcoded_secret_example():
    """Contains hardcoded credentials - security risk."""
    # BAD: Hardcoded API key
    api_key = "sk-1234567890abcdef1234567890abcdef"
    password = "super_secret_password_123"
    return {"api_key": api_key, "password": password}


def insecure_deserialization(data: bytes) -> object:
    """Vulnerable to arbitrary code execution via pickle."""
    # BAD: Deserializing untrusted data with pickle
    return pickle.loads(data)


def path_traversal_example(user_path: str) -> str:
    """Vulnerable to path traversal attacks."""
    # BAD: No validation of user-supplied path
    base_dir = "/var/data"
    full_path = os.path.join(base_dir, user_path)
    with open(full_path) as f:
        return f.read()


def exec_user_code(code: str) -> None:
    """Executes arbitrary user-supplied code."""
    # BAD: Executing untrusted code
    exec(code)
