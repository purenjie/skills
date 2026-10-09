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

    def test_capacity_is_checked_before_daily_selection(self) -> None:
        text = (REFERENCE_DIR / "daily-alignment.md").read_text(encoding="utf-8")
        self.assertLess(
            text.index("### Check capacity before selecting more work"),
            text.index("### Choose at most one proactive item when feasible"),
        )
        self.assertIn("A proposal is not an agreed change", text)
        self.assertIn("identify who can decide or help", text)
        self.assertIn("Do not add a strategic block", text)

    def test_curiosity_is_optional_and_exploration_needs_no_document(self) -> None:
        text = (REFERENCE_DIR / "daily-alignment.md").read_text(encoding="utf-8")
        self.assertIn("candidate, not an automatic winner", text)
        self.assertIn("Curiosity is optional", text)
        self.assertIn("No mandatory document or claim of production completion", text)
        self.assertIn("keep production and safety standards unchanged", text)

    def test_support_can_end_without_a_task_or_persistent_entry(self) -> None:
        main = MAIN_FILE.read_text(encoding="utf-8")
        daily = (REFERENCE_DIR / "daily-alignment.md").read_text(encoding="utf-8")
        self.assertIn("not therapy", main)
        self.assertIn("immediate safety concerns take precedence", main)
        self.assertIn("without adding a task, artifact, timer, or written entry", daily)
        self.assertIn("No note update is required", daily)
        self.assertIn("Do not log emotional disclosures", daily)
        self.assertIn("Do not abruptly demand empty time", daily)
        self.assertIn("Do not automatically refill freed time", daily)

    def test_old_compulsory_output_and_recovery_rules_are_removed(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [MAIN_FILE, *sorted(REFERENCE_DIR.glob("*.md"))]
        )
        for obsolete_rule in (
            "choose one daily winner and one independently useful artifact",
            "one winner and one concrete artifact are clear",
            "at least one proactive outcome survives even during an interrupt-heavy week",
            "no more than two or three independent maintenance commitments per week",
            "use the next working day's first block as the final fallback",
            "5. schedule a primary and fallback slot",
            "td task list --all --json --full",
        ):
            with self.subTest(rule=obsolete_rule):
                self.assertNotIn(obsolete_rule, text)

    def test_weekly_review_is_not_a_motivation_scorecard(self) -> None:
        text = (REFERENCE_DIR / "weekly-file.md").read_text(encoding="utf-8")
        self.assertIn("## Lightweight usefulness check", text)
        self.assertIn("do not create a scorecard, daily survey, or tracking layer", text)
        self.assertIn("Lack of excitement is not failure", text)
        self.assertIn("only if feasible, one strategic step", text)
        self.assertIn("do not store emotional disclosures", text)

    def test_integrations_preserve_authorization_and_optional_focus(self) -> None:
        main = MAIN_FILE.read_text(encoding="utf-8")
        integrations = (REFERENCE_DIR / "integrations.md").read_text(encoding="utf-8")
        maintenance = (REFERENCE_DIR / "interruption-and-maintenance.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("obtain explicit confirmation", main)
        self.assertIn("read back or otherwise verify the result", main)
        self.assertIn("code is not deployment", main)
        self.assertIn("do not require Focus for rest, support", integrations)
        self.assertIn("do not send it or change trackers without authorization", maintenance)
        self.assertIn("Never automatically assign the next working day's first block", maintenance)


if __name__ == "__main__":
    unittest.main()
