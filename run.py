from __future__ import annotations

import sys

import pytest


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        args = ["testcase", "-q"]
    return pytest.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
