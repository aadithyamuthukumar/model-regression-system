import json
import os

from classifier import classify_email, load_prompt
from schema import GoldenExample



def load_dataset(file_path: str) -> list[GoldenExample]:
    examples = []
    with open(file_path, "r") as f:
        for line in f:
            data = json.loads(line)
            examples.append(GoldenExample.model_validate(data))
    return examples

def evaluate(examples: list[GoldenExample], prompt_version: str) -> tuple[float, list[dict]]:
    if not examples:
            raise ValueError("No examples to evaluate") 
    
    results = []
    config = load_prompt(f"prompts/{prompt_version}.yaml")
    count = 0

    for i, example in enumerate(examples, start=1):
        prediction = classify_email(example.email, config)
        correct = prediction.category == example.expected_category
        results.append({
            "id": example.id,
            "expected_category": example.expected_category,
            "predicted_category": prediction.category,
            "correct": correct
            })
        if correct:
            count += 1
        print(f"Evaluated {i}/{len(examples)}")
    accuracy = count/len(examples)
    return accuracy, results

def save_results(accuracy: float, results: list[dict], prompt_version: str) -> None:

    os.makedirs("results", exist_ok=True)

    file_path = f"results/results_{prompt_version}.json"

    report = {
        "prompt_version": prompt_version,
        "accuracy": accuracy,
        "total_examples": len(results),
        "results": results
    }

    with open(file_path, "w") as f:
        json.dump(report, f, indent=2)

    



if __name__ == "__main__":
    examples = load_dataset("datasets/golden.jsonl")

    print(f"Loaded {len(examples)} examples")
    print(examples[0].email)
    print(examples[0].expected_category)

    prompt_version = "v2"
    
    accuracy, results = evaluate(examples, prompt_version)
    print(f"Accuracy: {accuracy:.2%}")
    for result in results:
        print(result)
    save_results(accuracy, results, prompt_version)



    
    