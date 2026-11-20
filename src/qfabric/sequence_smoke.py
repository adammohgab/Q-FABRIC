from __future__ import annotations

import json
from dataclasses import asdict

from .sequence_adapter import run_elementary_link_smoke_test


def main() -> None:
    result = run_elementary_link_smoke_test()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
