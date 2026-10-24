import json
import argparse
import sys


# Exit-code contract for the CLI:
#   0 - comparison succeeded (no regressions, or regressions reported but not enforced)
#   1 - regressions detected and --fail-on-regression was given
#   2 - invalid input or operational error (missing file, malformed JSON,
#       bad report structure, mismatched IDs, invalid arguments)
EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_ERROR = 2


class ReportError(ValueError):
    """Raised when an evaluation report is missing, malformed, or inconsistent."""


def load_results(file_path: str) -> dict:
    with open(file_path, "r") as f:
        try:
            report = json.load(f)
        except json.JSONDecodeError as e:
            raise ReportError(f"{file_path}: invalid JSON ({e})") from e

    validate_report(report, file_path)
    return report


def validate_report(report, file_path: str) -> None:
    if not isinstance(report, dict):
        raise ReportError(f"{file_path}: report must be a JSON object")

    for key in ("prompt_version", "accuracy", "results"):
        if key not in report:
            raise ReportError(f"{file_path}: missing required field '{key}'")

    if not isinstance(report["accuracy"], (int, float)) or isinstance(report["accuracy"], bool):
        raise ReportError(f"{file_path}: 'accuracy' must be a number")

    if not isinstance(report["results"], list):
        raise ReportError(f"{file_path}: 'results' must be a list")

    seen_ids = set()
    for index, item in enumerate(report["results"]):
        if not isinstance(item, dict):
            raise ReportError(f"{file_path}: results[{index}] must be an object")
        for key in ("id", "expected_category", "correct"):
            if key not in item:
                raise ReportError(f"{file_path}: results[{index}] missing required field '{key}'")
        if not isinstance(item["id"], str):
            raise ReportError(f"{file_path}: results[{index}] 'id' must be a string")
        if not isinstance(item["correct"], bool):
            raise ReportError(f"{file_path}: results[{index}] 'correct' must be true or false")
        if item["id"] in seen_ids:
            raise ReportError(f"{file_path}: duplicate result ID {item['id']}")
        seen_ids.add(item["id"])


def compare_results(baseline: str, candidates: list[str]) -> dict:


    baseline_report = load_results(baseline)
    baseline_by_id = {
        item["id"]: item
        for item in baseline_report["results"]
        }

    comparisons = {}

    for candidate_path in candidates:
        candidate_report = load_results(candidate_path)
        candidates_by_id = {
            item["id"]: item
            for item in candidate_report["results"]
        }

        regressions = []
        improvements= []

        if baseline_by_id.keys() != candidates_by_id.keys():
            missing = sorted(baseline_by_id.keys() - candidates_by_id.keys())
            extra = sorted(candidates_by_id.keys() - baseline_by_id.keys())
            raise ReportError(
                f"Baseline and candidate IDs do not match for {candidate_path} "
                f"(missing: {missing}, unexpected: {extra})"
            )

        if candidate_report["prompt_version"] in comparisons:
            raise ReportError(
                f"Duplicate candidate prompt_version {candidate_report['prompt_version']}"
            )

        accuracy_delta = (
            candidate_report["accuracy"] - baseline_report["accuracy"]
        )

        for id in baseline_by_id:
            baseline_item = baseline_by_id[id]
            candidate_item = candidates_by_id[id]

            if baseline_item["expected_category"] != candidate_item["expected_category"]:
                raise ReportError(f"Expected category mismatch for ID {id}")

            if baseline_item["correct"] and not candidate_item["correct"]:
                regressions.append({
                    "id": id,
                    "baseline": baseline_item,
                    "candidate": candidate_item
                })
            elif not baseline_item["correct"] and candidate_item["correct"]:
                improvements.append({
                    "id": id,
                    "baseline": baseline_item,
                    "candidate": candidate_item
                })



        comparisons[candidate_report["prompt_version"]] = {
            "baseline_accuracy": baseline_report["accuracy"],
            "candidate_accuracy": candidate_report["accuracy"],
            "regressions": regressions,
            "improvements": improvements,
            "accuracy_delta": accuracy_delta
        }

    return comparisons


def main(argv: list[str] | None = None) -> int:

    parser = argparse.ArgumentParser(
        description="Compare LLM evaluation results across prompt versions.",
        epilog="Exit codes: 0 = OK, 1 = regressions detected with "
               "--fail-on-regression, 2 = invalid input or error.",
    )

    parser.add_argument(
        "baseline",
        help="Path to the baseline results JSON file"
    )

    parser.add_argument(
        "candidates",
        nargs="+",
        help="Paths to the candidate evaluation reports"
    )

    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 if regressions are detected",
    )

    # argparse exits with code 2 on invalid arguments.
    args = parser.parse_args(argv)

    try:
        comparisons = compare_results(args.baseline, args.candidates)
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_ERROR

    regression_count = 0

    print(json.dumps(comparisons, indent=2))

    print("\nModel Regression Report")
    print("-----------------------")

    for version, result in comparisons.items():
        print(f"\nCandidate: {version}")

        print(f"Baseline Accuracy: {result['baseline_accuracy']:.2%}")
        print(f"Candidate Accuracy: {result['candidate_accuracy']:.2%}")
        print(
            f"Accuracy Change: "
            f"{result['accuracy_delta'] * 100:+.2f} percentage points"
        )

        print(f"Regressions: {len(result['regressions'])}")
        print(f"Improvements: {len(result['improvements'])}")

        regression_count += len(result["regressions"])

        for regression in result["regressions"]:
            print(f"Regressed example: {regression['id']}")


    if regression_count == 0:
        print("\nPASS: No regressions detected")
        return EXIT_OK

    if args.fail_on_regression:
        print(f"\nFAIL: Regressions detected ({regression_count})")
        return EXIT_REGRESSION

    print(
        f"\nWARNING: Regressions detected ({regression_count}); "
        f"not enforced without --fail-on-regression"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
