"""Create local-only login secrets without replacing site camera settings."""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path


def ensure_local_env(root: Path) -> tuple[bool, bool]:
    env_path = root / ".env"
    if not env_path.exists():
        template = root / ".env.example"
        if not template.exists():
            raise FileNotFoundError(".env.example is missing")
        env_path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    lines = env_path.read_text(encoding="utf-8-sig").splitlines()
    generated_owner = False
    generated_session = False

    def set_if_missing(name: str, value: str) -> bool:
        for index, line in enumerate(lines):
            if line.startswith(f"{name}="):
                if line.split("=", 1)[1].strip():
                    return False
                lines[index] = f"{name}={value}"
                return True
        lines.append(f"{name}={value}")
        return True

    if set_if_missing("RESEARCHER_ACCESS_KEY", secrets.token_urlsafe(18)):
        generated_owner = True
    if set_if_missing("SESSION_SECRET", secrets.token_urlsafe(48)):
        generated_session = True

    if generated_owner or generated_session:
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return generated_owner, generated_session


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    owner, session = ensure_local_env(args.root)
    print("Local login configuration ready.")
    if owner or session:
        print("New private credentials were saved only to this computer's .env file.")
    print("Do not include .env when sharing or creating a client ZIP.")
