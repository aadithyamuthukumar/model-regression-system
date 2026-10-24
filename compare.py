import json
import os
import argparse
import sys


def load_results(file_path: str) -> dict:
    with open(file_path, "r") as f:
        return json.load(f)


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
            raise ValueError("Baseline and candidate IDs do not match")

        accuracy_delta = (
            candidate_report["accuracy"] - baseline_report["accuracy"]
        )

        for id in baseline_by_id:
            baseline_item = baseline_by_id[id]
            candidate_item = candidates_by_id[id]

            if baseline_item["expected_category"] != candidate_item["expected_category"]:
                raise ValueError(f"Expected category mismatch for ID {id}")

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

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        description="Compare LLM evaluation results across prompt versions."
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

    args = parser.parse_args()


    comparisons = compare_results(args.baseline, args.candidates)

    has_regressions = False
    
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

        
        if result['regressions']:
            has_regressions = True

        for regression in result["regressions"]:
            print(f"Regressed example: {regression['id']}")


    if has_regressions:
        print("\nFAIL: Regressions detected")
        sys.exit(1)
    else:
        print("\nPASS: No regressions detected")
        sys.exit(0)

    
