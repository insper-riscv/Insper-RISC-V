"""Keep benchmark merge policy and shared cache paths consistent."""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class WorkflowPolicyTests(unittest.TestCase):
    """Preserve run lifetimes and shared caches."""

    def test_main_only_runs_keep_the_previous_main_baseline(self) -> None:
        """Benchmark merges with a bounded worker pool."""
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/embench.yml").read_text()
        )
        events = workflow.get("on", workflow.get(True))
        self.assertNotIn("pull_request", events)
        self.assertEqual(events["push"]["branches"], ["main"])
        self.assertEqual(workflow["concurrency"]["group"], "embench-main")
        self.assertFalse(workflow["concurrency"]["cancel-in-progress"])
        self.assertLessEqual(
            workflow["jobs"]["measure"]["strategy"]["max-parallel"], 4
        )
        self.assertIn("github.event.before", workflow["env"]["BASE_REF"])
        self.assertEqual(workflow["env"]["CANDIDATE_REF"], "${{ github.sha }}")
        self.assertEqual(workflow["jobs"]["plan"]["needs"], "eligible")
        self.assertIn("outputs.run", workflow["jobs"]["plan"]["if"])
        self.assertIn("outputs.run", workflow["jobs"]["embench"]["if"])

    def test_sdk_does_not_duplicate_push_and_pr_runs(self) -> None:
        """Check feature commits once through their PR event."""
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/sdk.yml").read_text()
        )
        events = workflow.get("on", workflow.get(True))
        self.assertEqual(events["push"]["branches"], ["main"])
        self.assertIn("pull_request", events)
        self.assertIn("pull_request.number", workflow["concurrency"]["group"])

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
        self.assertIn("push", workflow["jobs"]["comment"]["if"])
        self.assertIn("main", workflow["jobs"]["comment"]["if"])
        self.assertEqual(workflow["permissions"]["contents"], "read")
        self.assertEqual(workflow["permissions"]["pull-requests"], "write")
