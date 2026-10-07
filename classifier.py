import yaml

from dotenv import load_dotenv

from openai import OpenAI
from schema import ClassificationOutput, PromptConfig

load_dotenv()

def load_prompt(file_path: str) -> PromptConfig:
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)
    return PromptConfig(**data)

def classify_email(email: str, prompt_config: PromptConfig):
    prompt = prompt_config.system_prompt
    messages = []
    messages.append({
        "role": "system", 
        "content": prompt
        })
    for example in prompt_config.few_shot_examples:
        messages.append({
            "role": "user", 
            "content": example.email
            })
        messages.append({
            "role": "assistant", 
            "content": example.expected_output.model_dump_json()
            })
    messages.append({
        "role": "user", 
        "content": email
        })

    client = OpenAI()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"}
    )

    classification_result = response.choices[0].message.content
    validated_response = ClassificationOutput.model_validate_json(
        classification_result
    )

    return validated_response


if __name__ == "__main__":

    config = load_prompt("prompts/v1.yaml")

    result = classify_email(
        "Hi, I was charged twice for my subscription this month. Can I get a refund?",
        config
    )

    print(result.model_dump_json())
