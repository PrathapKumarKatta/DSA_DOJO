"""Run TaskFlow schema migrations during Vercel production builds."""

import os
import subprocess
import sys


def main() -> None:
    if os.environ.get("VERCEL_ENV") != "production":
        print("Skipping database migration outside a production build.")
        return
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("Set DATABASE_URL in the Vercel Production environment.")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


if __name__ == "__main__":
    main()
