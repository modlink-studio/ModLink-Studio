from __future__ import annotations

import unittest
from pathlib import Path


class QtCompatMigrationTest(unittest.TestCase):
    def test_core_and_sdk_have_no_direct_pyqtcore_imports(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        targets = (
            repo_root / "packages" / "modlink_core" / "modlink_core",
            repo_root / "packages" / "modlink_sdk" / "modlink_sdk",
        )

        offenders: list[str] = []
        for target in targets:
            for path in target.rglob("*.py"):
                content = path.read_text(encoding="utf-8")
                if "from PyQt6.QtCore" in content or "import PyQt6.QtCore" in content:
                    offenders.append(str(path.relative_to(repo_root)))

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
