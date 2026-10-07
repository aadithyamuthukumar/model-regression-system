from datetime import date
from typing import Literal
from pydantic import BaseModel
from pydantic.dataclasses import dataclass

class ClassificationOutput(BaseModel):
    category: Literal["billing", "technical", "account", "general"]
    summary: str

class FewShotExample(BaseModel):
    email: str
    expected_output: ClassificationOutput

@dataclass
class PromptConfig:
    version: str
    created_at: date
    system_prompt: str
    few_shot_examples: list[FewShotExample]