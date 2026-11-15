"""Check complete scores and reject partial comparisons."""

import unittest
from typing import Any

from benchmarks.embench import score


def fixture(
    profile: str, cycles: list[int], multiplier: float = 1.0
) -> dict[str, Any]:
    """Build consistent program ratios without a CPU model."""
    return {
        "profile": profile,
        "provenance": {"contract": {"compiler": "fixed"}},
        "suite": {"programs": ["a", "b"], "workload": "ci"},
        "results": [
            {
                "program": name,
                "status": "pass",
                "cycles": count,
                "instructions": 10,
                "operations": {
                    "branching": 1,
                    "memory": 2,
                    "compute": 3,
                    "other": 4,
                },
                "score_per_mhz": multiplier * 100 / count,
            }
            for name, count in zip(("a", "b"), cycles, strict=True)
        ],
    }


class ScoreTests(unittest.TestCase):
    """Require complete scores and equal profile weights."""

    def expected(self) -> dict[str, Any]:
        """Freeze two source commits, as the workflow plan does."""
        return {
            "profiles": ["rv32i", "rv32im"],
            "programs": ["a", "b"],
            "revisions": {"base": "a" * 40, "candidate": "b" * 40},
        }

    def test_geometric_total_and_profile_scores(self) -> None:
        """Combine gains and regressions geometrically."""
        paired = {
            "rv32i": (
                fixture("rv32i", [100, 200]),
                fixture("rv32i", [50, 100]),
            ),
            "rv32im": (
                fixture("rv32im", [100, 200]),
                fixture("rv32im", [400, 800]),
            ),
        }
        result = score.calculate(self.expected(), paired)
        self.assertEqual(result["status"], "complete")
        self.assertAlmostEqual(result["relative_index"], 100 * (0.5**0.5))
        self.assertAlmostEqual(
            result["delta_percent"], result["relative_index"] - 100
        )
        self.assertEqual(
            [item["relative_index"] for item in result["profiles"]],
            [200.0, 25.0],
        )
        self.assertIn("main = 100", score.markdown(result))
        self.assertIn("not measured FPGA", score.markdown(result))

    def test_identical_cpu_scores_one_hundred(self) -> None:
        """No change gives exactly the neutral relative index."""
        paired = {
            name: (fixture(name, [100, 200]), fixture(name, [100, 200]))
            for name in self.expected()["profiles"]
        }
        self.assertAlmostEqual(
            score.calculate(self.expected(), paired)["relative_index"], 100
        )

    def test_partial_profile_or_failed_program_has_no_total(self) -> None:
        """Never drop unavailable or failed rows from totals."""
        paired = {
            "rv32i": (
                fixture("rv32i", [100, 200]),
                fixture("rv32i", [50, 100]),
            )
        }
        self.assertIsNone(
            score.calculate(self.expected(), paired)["relative_index"]
        )
        for mutation in ("missing", "failed", "contract", "invalid-counts"):
            before, head = (
                fixture("rv32im", [100, 200]),
                fixture("rv32im", [100, 200]),
            )
            if mutation == "missing":
                head["results"].pop()
            elif mutation == "failed":
                head["results"][0]["status"] = "failed"
            elif mutation == "contract":
                head["provenance"]["contract"] = {"compiler": "changed"}
            else:
                head["results"][0]["instructions"] = 99
            paired["rv32im"] = (before, head)
            with self.subTest(mutation=mutation):
                self.assertEqual(
                    score.calculate(self.expected(), paired)["status"],
                    "incomplete",
                )

    def test_renamed_profile_is_not_a_valid_pair(self) -> None:
        """A baseline from another profile cannot supply the score."""
        with self.assertRaises(ValueError):
            score.profile_score(
                fixture("rv32i", [100, 200]), fixture("rv32im", [100, 200])
            )

    def test_reference_scores_do_not_define_the_relative_speedup(self) -> None:
        """Reference units do not change the relative speedup."""
        base, head = fixture("rv32i", [100, 200]), fixture("rv32i", [50, 100])
        first = score.profile_score(base, head)
        for data in (base, head):
            for row in data["results"]:
                row["score_per_mhz"] *= 5
        second = score.profile_score(base, head)
        self.assertEqual(first["relative_index"], second["relative_index"])
        self.assertAlmostEqual(
            second["head_score_per_mhz"], first["head_score_per_mhz"] * 5
        )


if __name__ == "__main__":
    unittest.main()
