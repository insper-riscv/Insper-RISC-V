"""Keep benchmark merge policy and shared cache paths consistent."""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class WorkflowPolicyTests(unittest.TestCase):
    """Preserve run lifetimes and shared caches."""

    def test_started_runs_are_not_cancelled_and_main_warms_the_cache(
        self,
    ) -> None:
        """Let merges proceed while benchmarks run."""
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/embench.yml").read_text()
        )
        events = workflow.get("on", workflow.get(True))
        self.assertFalse(workflow["concurrency"]["cancel-in-progress"])
        self.assertEqual(events["push"]["branches"], ["main"])
        self.assertNotIn("closed", events["pull_request"]["types"])
        self.assertIn("refs/heads/main", workflow["env"]["BASE_REF"])
        self.assertNotIn("pull_request.base.sha", workflow["env"]["BASE_REF"])
        self.assertIn(
            "pull_request.head.sha", workflow["env"]["CANDIDATE_REF"]
        )

    def test_both_sides_restore_and_save_the_same_content_key_paths(
        self,
    ) -> None:
        """Share cache versions by using content-keyed paths."""
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/embench.yml").read_text()
        )
        steps = workflow["jobs"]["measure"]["steps"]
        restores = [
            step["with"]["path"]
            for step in steps
            if step.get("uses", "").startswith("actions/cache/restore")
        ]
        saves = [
            step["with"]["path"]
            for step in steps
            if step.get("uses", "").startswith("actions/cache/save")
        ]
        self.assertEqual(restores, saves)
        self.assertEqual(len(restores), 2)
        self.assertTrue(
            all("steps.keys.outputs." in path for path in restores)
        )
        self.assertNotIn("cache/base", restores)
        self.assertNotIn("cache/candidate", restores)

    def test_write_token_publisher_never_checks_out_the_pr(self) -> None:
        """Render bot comments using trusted code only."""
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/embench-comment.yml").read_text()
        )
        steps = workflow["jobs"]["comment"]["steps"]
        checkouts = [
            step
            for step in steps
            if step.get("uses", "").startswith("actions/checkout")
        ]
        self.assertEqual(len(checkouts), 1)
        self.assertEqual(checkouts[0]["with"]["ref"], "main")
        self.assertFalse(checkouts[0]["with"]["persist-credentials"])
        self.assertEqual(workflow["permissions"]["contents"], "read")
        self.assertEqual(workflow["permissions"]["pull-requests"], "write")
