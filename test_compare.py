import unittest
import tempfile
import json
from pathlib import Path
from compare import compare_results


class TestCompareResults(unittest.TestCase):

    def write_report(self, directory, filename, data):
        file_path = Path(directory) / filename

        with open(file_path, "w") as f:
            json.dump(data, f)
        return str(file_path)
    
    
    def test_regressions_and_improvements(self):
        baseline = {
            "prompt_version": "v1",
            "accuracy": 0.5,
            "results": [
                {"id": "001", "expected_category": "account", "correct": False},
                {"id": "002", "expected_category": "account", "correct": True}
            ]
        }

        candidate = {
            "prompt_version": "v2",
            "accuracy": 0.5,
            "results": [
                {"id": "001", "expected_category": "account", "correct": True},
                {"id": "002", "expected_category": "account", "correct": False}
            ]
        }

        with tempfile.TemporaryDirectory() as directory:
            baseline_path = self.write_report(directory, "baseline.json", baseline)
            candidate_path = self.write_report(directory, "candidate.json", candidate)

            comparison = compare_results(baseline_path, [candidate_path])

            self.assertEqual(len(comparison["v2"]["regressions"]), 1)
            self.assertEqual(len(comparison["v2"]["improvements"]), 1)
            self.assertEqual(comparison["v2"]["accuracy_delta"], 0.0)

            self.assertEqual(
                comparison["v2"]["regressions"][0]["id"],
                "002"
            )
            self.assertEqual(
                comparison["v2"]["improvements"][0]["id"],
                "001"
            )

    def test_mismatched_ids(self):
        baseline = {
            "prompt_version": "v1",
            "accuracy": 0.5,
            "results": [
                {"id": "001", "expected_category": "account", "correct": False},
                {"id": "002", "expected_category": "account", "correct": True}
            ]
        }

        candidate = {
            "prompt_version": "v2",
            "accuracy": 0.5,
            "results": [
                {"id": "001", "expected_category": "account", "correct": True},
                {"id": "003", "expected_category": "account", "correct": False}
            ]
        }

        with tempfile.TemporaryDirectory() as directory:
            baseline_path = self.write_report(directory, "baseline.json", baseline)
            candidate_path = self.write_report(directory, "candidate.json", candidate)

            with self.assertRaises(ValueError):
                compare_results(baseline_path, [candidate_path])
                
    def test_no_regressions_or_improvements(self):
        baseline = {
            "prompt_version": "v1",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "account", "correct": True},
                {"id": "002", "expected_category": "account", "correct": True}
            ]
        }

        candidate = {
            "prompt_version": "v2",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "account", "correct": True},
                {"id": "002", "expected_category": "account", "correct": True}
            ]
        }

        with tempfile.TemporaryDirectory() as directory:
            baseline_path = self.write_report(directory, "baseline.json", baseline)
            candidate_path = self.write_report(directory, "candidate.json", candidate)

            comparison = compare_results(baseline_path, [candidate_path])

            self.assertEqual(len(comparison["v2"]["regressions"]), 0)
            self.assertEqual(len(comparison["v2"]["improvements"]), 0)
            self.assertEqual(comparison["v2"]["accuracy_delta"], 0.0)

    def test_multiple_candidates(self):
        baseline= {
            "prompt_version": "v1",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "account", "correct": True},
                {"id": "002", "expected_category": "account", "correct": True}
              ]
         }

        candidate1 = {
            "prompt_version": "v2",
            "accuracy": 0.5,
            "results": [
                {"id": "001", "expected_category": "account", "correct": True},
                {"id": "002", "expected_category": "account", "correct": False}
              ]
         }

        candidate2 = {
            "prompt_version": "v3",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "account", "correct": True},
                {"id": "002", "expected_category": "account", "correct": True}
              ]
         }

        with tempfile.TemporaryDirectory() as directory:
            baseline_path = self.write_report(directory, "baseline.json", baseline)
            candidate1_path = self.write_report(directory, "candidate1.json", candidate1)
            candidate2_path = self.write_report(directory, "candidate2.json", candidate2)

            comparison = compare_results(baseline_path, [candidate1_path, candidate2_path])

            self.assertEqual(len(comparison["v2"]["regressions"]), 1)
            self.assertEqual(len(comparison["v2"]["improvements"]), 0)
            self.assertEqual(comparison["v2"]["accuracy_delta"], -0.5)
            self.assertEqual(len(comparison["v3"]["regressions"]), 0)
            self.assertEqual(len(comparison["v3"]["improvements"]), 0)
            self.assertEqual(comparison["v3"]["accuracy_delta"], 0.0)

            self.assertEqual(comparison["v2"]["regressions"][0]["id"],"002")

    def test_expected_category_mismatch(self):
        baseline = {
            "prompt_version": "v1",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "account", "correct": True}
            ]
        }

        candidate = {
            "prompt_version": "v2",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "technical", "correct": True}
            ]
        }

        with tempfile.TemporaryDirectory() as directory:
            baseline_path = self.write_report(directory, "baseline.json", baseline)
            candidate_path = self.write_report(directory, "candidate.json", candidate)

            with self.assertRaises(ValueError) as context:
                compare_results(baseline_path, [candidate_path])

            self.assertIn("Expected category mismatch for ID 001", str(context.exception))

if __name__ == "__main__":
    unittest.main()