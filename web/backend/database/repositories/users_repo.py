from __future__ import annotations

from typing import Any

from core.database import open_db


def find_user_by_email(email: str):
    with open_db() as conn:
        return conn.execute("SELECT email, password_hash, role, created_at FROM users WHERE email = ?", (email,)).fetchone()


def create_user(email: str, password_hash: str, role: str, created_at: int) -> None:
    with open_db() as conn:
        conn.execute(
            "INSERT INTO users (email, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (email, password_hash, role, created_at),
        )
        conn.commit()


def update_user_password(email: str, password_hash: str) -> None:
    with open_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, email))
        conn.commit()


def list_users() -> dict[str, Any]:
    with open_db() as conn:
        rows = conn.execute(
            "SELECT email, role, created_at FROM users ORDER BY created_at DESC").fetchall()
    return {
        "items": [
            {
                "email": r["email"],
                "role": r["role"],
                "created_at": int(r["created_at"]),
            }
            for r in rows
        ]
    }


def update_user_role(email: str, role: str) -> None:
    with open_db() as conn:
        conn.execute(
            "UPDATE users SET role = ? WHERE email = ?", (role, email))
        conn.commit()


def delete_user(email: str) -> None:
    with open_db() as conn:
        conn.execute(
            "DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
