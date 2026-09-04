from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).parents[1]
MAIN_FILE = SKILL_DIR / "SKILL.md"
REFERENCE_DIR = SKILL_DIR / "references"
MARKDOWN_LINK = re.compile(r"\]\(([^)]+\.md)\)")


class SkillStructureTests(unittest.TestCase):
    def test_entrypoint_stays_a_small_router(self) -> None:
        text = MAIN_FILE.read_text(encoding="utf-8")

        self.assertLessEqual(len(text.splitlines()), 180)
        for implementation_detail in (
            "/Users/",
            "LaunchAgent:",
            "raycast_focus.py",
            "td auth status",
        ):
            self.assertNotIn(implementation_detail, text)

    def test_all_markdown_links_resolve(self) -> None:
        markdown_files = [MAIN_FILE, *sorted(REFERENCE_DIR.glob("*.md"))]

        for source in markdown_files:
            for target in MARKDOWN_LINK.findall(source.read_text(encoding="utf-8")):
                resolved = (source.parent / target).resolve()
                self.assertTrue(resolved.is_file(), f"{source} links to missing {target}")

    def test_every_reference_is_discoverable(self) -> None:
        markdown_files = [MAIN_FILE, *sorted(REFERENCE_DIR.glob("*.md"))]
        linked = {
            (source.parent / target).resolve()
            for source in markdown_files
            for target in MARKDOWN_LINK.findall(source.read_text(encoding="utf-8"))
        }

        for reference in REFERENCE_DIR.glob("*.md"):
            self.assertIn(reference.resolve(), linked, f"unrouted reference: {reference}")

    def test_frontmatter_name_matches_folder(self) -> None:
        text = MAIN_FILE.read_text(encoding="utf-8")
        match = re.search(r"^name:\s*(\S+)\s*$", text, re.MULTILINE)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1), SKILL_DIR.name)


if __name__ == "__main__":
    unittest.main()
