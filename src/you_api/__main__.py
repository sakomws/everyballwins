"""Entry point so ``python -m you_api`` starts the service."""

from .service import main

if __name__ == "__main__":
    raise SystemExit(main())
