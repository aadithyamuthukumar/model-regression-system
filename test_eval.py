import unittest
from types import SimpleNamespace
from unittest.mock import patch

import eval as eval_module


class TestEvalCli(unittest.TestCase):

    def run_main(self, argv):
        examples = [
            SimpleNamespace(
                email="Test email",
                expected_category="general",
            )
        ]
        results = [
            {
                "id": "001",
                "expected_category": "general",
                "predicted_category": "general",
                "correct": True,
            }
        ]

        with patch.object(eval_module, "load_dataset", return_value=examples), \
             patch.object(eval_module, "evaluate", return_value=(1.0, results)) as evaluate, \
             patch.object(eval_module, "save_results") as save_results:
            eval_module.main(argv)

        return examples, results, evaluate, save_results

    def test_prompt_version_argument_is_used(self):
        examples, results, evaluate, save_results = self.run_main(
            ["--prompt-version", "v2"]
        )

        evaluate.assert_called_once_with(examples, "v2")
        save_results.assert_called_once_with(1.0, results, "v2")

    def test_prompt_version_defaults_to_v1(self):
        examples, results, evaluate, save_results = self.run_main([])

        evaluate.assert_called_once_with(examples, "v1")
        save_results.assert_called_once_with(1.0, results, "v1")


if __name__ == "__main__":
    unittest.main()
