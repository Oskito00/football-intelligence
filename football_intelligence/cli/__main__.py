"""Module entrypoint for `python -m football_intelligence.cli`."""

import sys

from football_intelligence.cli.main import main


if __name__ == "__main__":
    sys.exit(main())
