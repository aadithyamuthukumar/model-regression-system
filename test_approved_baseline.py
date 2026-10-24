import json
import unittest
from pathlib import Path

import yaml

from compare import compare_results, load_results


REPO_ROOT = Path(__file__).resolve().parent
BASELINE = REPO_ROOT / "baselines" / "approved_v1.jsonl"
GOLDEN = REPO_ROOT / "datasets" / "golden.jsonl"
PROMPT = REPO_ROOT / "prompts" / "v1.yaml"

CATEGORIES = {"billing", "technical", "account", "general"}


class TestApprovedBaseline(unittest.TestCase):
    """The approved baseline must be a consistent evaluation report for the golden dataset.

    Note: despite the .jsonl extension, the baseline (like results/results_v1.jsonl)
    is a single JSON report object as written by eval.save_results.
    """

    @classmethod
    def setUpClass(cls):
        cls.report = load_results(str(BASELINE))
        with open(GOLDEN) as f:
            cls.golden = {
                example["id"]: example
                for example in map(json.loads, filter(str.strip, f))
            }

    def test_prompt_version_matches_prompt_file(self):
        with open(PROMPT) as f:
            prompt_version = yaml.safe_load(f)["version"]
        self.assertEqual(self.report["prompt_version"], prompt_version)

    def test_covers_exactly_the_golden_ids(self):
        ids = [item["id"] for item in self.report["results"]]
        self.assertEqual(sorted(ids), sorted(self.golden))
        self.assertEqual(self.report["total_examples"], len(self.golden))

    def test_results_are_consistent(self):
        for item in self.report["results"]:
            with self.subTest(id=item["id"]):
                self.assertEqual(
                    item["expected_category"],
                    self.golden[item["id"]]["expected_category"]
                )
                self.assertIn(item["predicted_category"], CATEGORIES)
                self.assertEqual(
                    item["correct"],
                    item["predicted_category"] == item["expected_category"]
                )

    def test_accuracy_matches_results(self):
        results = self.report["results"]
        accuracy = sum(item["correct"] for item in results) / len(results)
        self.assertAlmostEqual(self.report["accuracy"], accuracy)

    def test_baseline_compares_cleanly_against_itself(self):
        comparison = compare_results(str(BASELINE), [str(BASELINE)])
        result = comparison[self.report["prompt_version"]]
        self.assertEqual(result["regressions"], [])
        self.assertEqual(result["improvements"], [])


if __name__ == "__main__":
    unittest.main()
