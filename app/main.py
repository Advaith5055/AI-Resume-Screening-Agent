"""Main entry point for AI Resume Screening Agent."""

import sys
from app.config import APP_ENV, LOG_LEVEL, OUTPUTS_DIR, RESUMES_DIR


def main() -> int:
    """Run minimal entrypoint confirming the agent environment is initialized."""
    print("=" * 60)
    print("  AI Resume Screening Agent - System Initialized")
    print("=" * 60)
    print(f"Environment : {APP_ENV}")
    print(f"Log Level   : {LOG_LEVEL}")
    print(f"Resumes Dir : {RESUMES_DIR}")
    print(f"Outputs Dir : {OUTPUTS_DIR}")
    print("-" * 60)
    print("Status      : Ready. Foundation modules initialized.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
