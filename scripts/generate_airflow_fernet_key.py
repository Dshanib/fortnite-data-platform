#!/usr/bin/env python3
"""Print a new AIRFLOW_FERNET_KEY for local .env only (never commit .env)."""

from __future__ import annotations

import base64
import os


def main() -> None:
    print(base64.urlsafe_b64encode(os.urandom(32)).decode())


if __name__ == "__main__":
    main()
