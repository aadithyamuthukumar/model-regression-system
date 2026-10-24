import sys
import unittest
import tempfile
import json
import subprocess
from pathlib import Path
from compare import compare_results, ReportError, EXIT_OK, EXIT_REGRESSION, EXIT_ERROR


REPO_ROOT = Path(__file__).resolve().parent
COMPARE_SCRIPT = REPO_ROOT / "compare.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(COMPARE_SCRIPT), *map(str, args)],
        capture_output=True,
        text=True
    )


def report(version, accuracy, outcomes, category="billing"):
    """Build a report from a list of (id, correct) pairs."""
    return {
        "prompt_version": version,
        "accuracy": accuracy,
        "results": [
            {"id": id, "expected_category": category, "correct": correct}
            for id, correct in outcomes
        ]
    }


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

    def test_cli_fails_on_regression(self):
        baseline = {
            "prompt_version": "v1",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "billing", "correct": True}
            ]
        }

        candidate = {
            "prompt_version": "v2",
            "accuracy": 0.0,
            "results": [
                {"id": "001", "expected_category": "billing", "correct": False}
            ]
        }

        with tempfile.TemporaryDirectory() as directory:
            baseline_path = self.write_report(directory, "baseline.json", baseline)
            candidate_path = self.write_report(directory, "candidate.json", candidate)

            result = run_cli(baseline_path, candidate_path, "--fail-on-regression")

            self.assertEqual(result.returncode, EXIT_REGRESSION)
            self.assertIn("FAIL: Regressions detected", result.stdout)
            self.assertIn("Regressed example: 001", result.stdout)

    def test_cli_passes_without_regression(self):
        baseline = {
            "prompt_version": "v1",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "billing", "correct": True}
            ]
        }

        candidate = {
            "prompt_version": "v2",
            "accuracy": 1.0,
            "results": [
                {"id": "001", "expected_category": "billing", "correct": True}
            ]
        }

        with tempfile.TemporaryDirectory() as directory:
            baseline_path = self.write_report(directory, "baseline.json", baseline)
            candidate_path = self.write_report(directory, "candidate.json", candidate)

            result = run_cli(baseline_path, candidate_path)

            self.assertEqual(result.returncode, EXIT_OK)
            self.assertIn("PASS: No regressions detected", result.stdout)

    def test_cli_fails_if_any_candidate_regresses(self):
        baseline = report("v1", 1.0, [("001", True)])
        passing = report("v2", 1.0, [("001", True)])
        regressing = report("v3", 0.0, [("001", False)])

        with tempfile.TemporaryDirectory() as directory:
            baseline_path = self.write_report(directory, "baseline.json", baseline)
            passing_path = self.write_report(directory, "passing.json", passing)
            regressing_path = self.write_report(directory, "regressing.json", regressing)

            result = run_cli(baseline_path, passing_path, regressing_path, "--fail-on-regression")

            self.assertEqual(result.returncode, EXIT_REGRESSION)
            self.assertIn("FAIL: Regressions detected", result.stdout)


class TestCliExitCodes(unittest.TestCase):
    """Exit-code contract: 0 = OK, 1 = enforced regression, 2 = invalid input/error."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_json(self, filename, data):
        path = self.directory / filename
        path.write_text(json.dumps(data))
        return path

    def write_text(self, filename, text):
        path = self.directory / filename
        path.write_text(text)
        return path

    def assert_error_exit(self, result):
        self.assertEqual(result.returncode, EXIT_ERROR, result.stdout + result.stderr)
        self.assertNotIn("FAIL: Regressions detected", result.stdout)
        self.assertNotIn("PASS", result.stdout)

    # --- regression handling ---

    def test_regression_in_strict_mode_exits_1(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True), ("002", True)]))
        candidate = self.write_json("c.json", report("v2", 0.5, [("001", True), ("002", False)]))

        result = run_cli(baseline, candidate, "--fail-on-regression")

        self.assertEqual(result.returncode, EXIT_REGRESSION)
        self.assertIn("FAIL: Regressions detected (1)", result.stdout)
        self.assertIn("Regressed example: 002", result.stdout)

    def test_regression_in_reporting_mode_exits_0_with_warning(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True), ("002", True)]))
        candidate = self.write_json("c.json", report("v2", 0.5, [("001", True), ("002", False)]))

        result = run_cli(baseline, candidate)

        self.assertEqual(result.returncode, EXIT_OK)
        self.assertIn("Regressions: 1", result.stdout)
        self.assertIn("Regressed example: 002", result.stdout)
        self.assertIn("WARNING: Regressions detected (1)", result.stdout)
        self.assertNotIn("FAIL", result.stdout)

    def test_no_regressions_in_strict_mode_exits_0(self):
        baseline = self.write_json("b.json", report("v1", 0.5, [("001", True), ("002", False)]))
        candidate = self.write_json("c.json", report("v2", 1.0, [("001", True), ("002", True)]))

        result = run_cli(baseline, candidate, "--fail-on-regression")

        self.assertEqual(result.returncode, EXIT_OK)
        self.assertIn("Improvements: 1", result.stdout)
        self.assertIn("PASS: No regressions detected", result.stdout)

    def test_regression_and_improvement_counts(self):
        baseline = self.write_json("b.json", report(
            "v1", 0.5, [("001", True), ("002", True), ("003", False), ("004", False)]))
        candidate = self.write_json("c.json", report(
            "v2", 0.25, [("001", False), ("002", False), ("003", True), ("004", False)]))

        comparison = compare_results(str(baseline), [str(candidate)])["v2"]
        self.assertEqual([r["id"] for r in comparison["regressions"]], ["001", "002"])
        self.assertEqual([i["id"] for i in comparison["improvements"]], ["003"])
        self.assertEqual(comparison["accuracy_delta"], -0.25)

        result = run_cli(baseline, candidate, "--fail-on-regression")
        self.assertEqual(result.returncode, EXIT_REGRESSION)
        self.assertIn("Regressions: 2", result.stdout)
        self.assertIn("Improvements: 1", result.stdout)
        self.assertIn("FAIL: Regressions detected (2)", result.stdout)

    # --- invalid input must exit 2, never 1 ---

    def test_missing_baseline_file(self):
        candidate = self.write_json("c.json", report("v2", 1.0, [("001", True)]))
        result = run_cli(self.directory / "missing.json", candidate, "--fail-on-regression")
        self.assert_error_exit(result)
        self.assertIn("ERROR", result.stderr)

    def test_missing_candidate_file(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)]))
        result = run_cli(baseline, self.directory / "missing.json", "--fail-on-regression")
        self.assert_error_exit(result)

    def test_malformed_json(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)]))
        candidate = self.write_text("c.json", '{"prompt_version": "v2", "results": [')
        result = run_cli(baseline, candidate, "--fail-on-regression")
        self.assert_error_exit(result)
        self.assertIn("invalid JSON", result.stderr)

    def test_empty_file(self):
        baseline = self.write_text("b.json", "")
        candidate = self.write_json("c.json", report("v2", 1.0, [("001", True)]))
        self.assert_error_exit(run_cli(baseline, candidate, "--fail-on-regression"))

    def test_missing_required_report_field(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)]))
        candidate = self.write_json("c.json", {"prompt_version": "v2", "accuracy": 1.0})
        result = run_cli(baseline, candidate, "--fail-on-regression")
        self.assert_error_exit(result)
        self.assertIn("'results'", result.stderr)

    def test_result_missing_id(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)]))
        candidate = self.write_json("c.json", {
            "prompt_version": "v2", "accuracy": 1.0,
            "results": [{"expected_category": "billing", "correct": True}]
        })
        result = run_cli(baseline, candidate, "--fail-on-regression")
        self.assert_error_exit(result)
        self.assertIn("'id'", result.stderr)

    def test_mismatched_ids_exit_2_not_1(self):
        # A candidate missing a baseline-correct example must not be read as a regression.
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True), ("002", True)]))
        candidate = self.write_json("c.json", report("v2", 1.0, [("001", True), ("003", True)]))
        result = run_cli(baseline, candidate, "--fail-on-regression")
        self.assert_error_exit(result)
        self.assertIn("missing: ['002']", result.stderr)
        self.assertIn("unexpected: ['003']", result.stderr)

    def test_duplicate_ids_rejected(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)]))
        candidate = self.write_json("c.json", report("v2", 0.5, [("001", True), ("001", False)]))

        with self.assertRaises(ReportError):
            compare_results(str(baseline), [str(candidate)])

        result = run_cli(baseline, candidate, "--fail-on-regression")
        self.assert_error_exit(result)
        self.assertIn("duplicate result ID 001", result.stderr)

    def test_duplicate_candidate_versions_rejected(self):
        # Two candidates with the same prompt_version would otherwise overwrite each other.
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)]))
        regressing = self.write_json("c1.json", report("v2", 0.0, [("001", False)]))
        passing = self.write_json("c2.json", report("v2", 1.0, [("001", True)]))
        result = run_cli(baseline, regressing, passing, "--fail-on-regression")
        self.assert_error_exit(result)

    def test_expected_category_mismatch_exits_2(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)], category="billing"))
        candidate = self.write_json("c.json", report("v2", 1.0, [("001", True)], category="account"))
        self.assert_error_exit(run_cli(baseline, candidate, "--fail-on-regression"))

    def test_non_boolean_correct_field(self):
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)]))
        candidate = self.write_json("c.json", report("v2", 1.0, [("001", "yes")]))
        self.assert_error_exit(run_cli(baseline, candidate, "--fail-on-regression"))

    def test_invalid_arguments(self):
        self.assertEqual(run_cli().returncode, EXIT_ERROR)
        baseline = self.write_json("b.json", report("v1", 1.0, [("001", True)]))
        self.assertEqual(run_cli(baseline).returncode, EXIT_ERROR)
        self.assertEqual(run_cli(baseline, baseline, "--no-such-flag").returncode, EXIT_ERROR)


class TestCommittedFixtures(unittest.TestCase):
    """The same fixtures the GitHub Actions workflow uses."""

    def test_fixtures_exist(self):
        for name in ("baseline.json", "candidate_pass.json",
                     "candidate_fail.json", "candidate_mismatched_ids.json"):
            self.assertTrue((FIXTURES / name).is_file(), name)

    def test_passing_candidate_accepted(self):
        result = run_cli(FIXTURES / "baseline.json", FIXTURES / "candidate_pass.json",
                         "--fail-on-regression")
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)

    def test_failing_candidate_rejected_as_regression(self):
        result = run_cli(FIXTURES / "baseline.json", FIXTURES / "candidate_fail.json",
                         "--fail-on-regression")
        self.assertEqual(result.returncode, EXIT_REGRESSION, result.stderr)
        self.assertIn("Regressed example: 002", result.stdout)

    def test_failing_candidate_only_reported_without_flag(self):
        result = run_cli(FIXTURES / "baseline.json", FIXTURES / "candidate_fail.json")
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)

    def test_mismatched_fixture_is_an_error(self):
        result = run_cli(FIXTURES / "baseline.json", FIXTURES / "candidate_mismatched_ids.json",
                         "--fail-on-regression")
        self.assertEqual(result.returncode, EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()