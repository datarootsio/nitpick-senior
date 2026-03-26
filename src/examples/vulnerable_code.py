"""Sample code with security issues for testing semgrep integration."""

import subprocess
import sqlite3


def execute_user_code(user_input: str) -> any:
    """Execute user-provided code - DANGEROUS!"""
    # semgrep: python.lang.security.audit.eval-detected
    return eval(user_input)


def run_dynamic_code(code_string: str) -> None:
    """Run dynamic code - DANGEROUS!"""
    # semgrep: python.lang.security.audit.exec-detected
    exec(code_string)


def get_user_data(db_path: str, username: str) -> list:
    """Fetch user data with SQL injection vulnerability."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # semgrep: python.lang.security.audit.sqli
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()


def run_command(user_command: str) -> str:
    """Run a shell command - command injection risk."""
    # semgrep: python.lang.security.audit.subprocess-shell-true
    result = subprocess.run(user_command, shell=True, capture_output=True)
    return result.stdout.decode()


# Hardcoded credentials - bad practice
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "super_secret_password_123"


def connect_to_service():
    """Connect using hardcoded credentials."""
    return {
        "api_key": API_KEY,
        "password": DATABASE_PASSWORD,
    }
