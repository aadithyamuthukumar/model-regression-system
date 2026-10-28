# Model Regression System

A small, testable regression harness for versioned LLM prompts. The project
evaluates an email-classification prompt against a fixed golden dataset, saves
per-example outcomes, and compares a candidate report with an approved
baseline.

Aggregate accuracy alone can hide important behavior changes. A candidate can
improve overall while becoming wrong on an example the baseline handled
correctly. This project reports those per-example regressions and can enforce
them as a CI gate.

## Experiment Results

The committed reports capture an experiment over 40 golden examples:

| Prompt | Accuracy | Correct | Improvements | Regressions |
| --- | ---: | ---: | ---: | ---: |
| v1 baseline | 90% | 36/40 | - | - |
| v2 candidate | 95% | 38/40 | 3 | 1 |

Compared with v1, v2 improved examples `005`, `014`, and `039`, but regressed
example `033`. Example `040` was incorrect in both runs. The net change is
therefore two additional correct examples and **+5 percentage points**, while
still containing one behavior regression.

This distinction matters in production systems. An aggregate gain may not be
acceptable if a safety-critical, contractual, or otherwise important case
gets worse. Running the comparison with `--fail-on-regression` makes any
correct-to-incorrect transition fail the gate, including this v2 result.

The experiment artifacts are:

- Approved baseline: `baselines/approved_v1.jsonl`
- Historical v1 report: `results/results_v1.jsonl`
- Candidate report: `results/results_v2.json`

The two `.jsonl` report files above are historical filenames. They contain one
multiline JSON object, not JSON Lines. `datasets/golden.jsonl` is genuine JSON
Lines, with one example per line. New reports produced by `eval.py` use the
`.json` extension.

## Architecture

```text
datasets/golden.jsonl
        |
        v
eval.py -> prompts/<version>.yaml -> classifier.py -> OpenAI API
        |                                      |
        |                                      v
        +---------------------------- validated category
        |
        v
results/results_<version>.json
        |
        v
compare.py <approved baseline> <candidate reports>
        |
        +-> regressions, improvements, accuracy delta, exit code
```

The main components are:

| Path | Responsibility |
| --- | --- |
| `classifier.py` | Loads prompt YAML, builds few-shot messages, calls `gpt-4o-mini`, and validates JSON output. |
| `eval.py` | Loads the golden dataset, evaluates one prompt version, computes category accuracy, and writes a result report. |
| `compare.py` | Validates reports and compares one baseline with one or more candidates by example ID. |
| `schema.py` | Defines Pydantic models for prompts, classifications, and golden examples. |
| `prompts/` | Contains the versioned v1 and v2 prompt configurations. |
| `datasets/golden.jsonl` | Contains 40 labeled email examples across four categories. |
| `baselines/` | Contains the approved v1 evaluation report. |
| `results/` | Contains committed experiment reports and receives new evaluation output. |
| `tests/fixtures/` | Contains small committed reports for offline regression-gate tests. |
| `.github/workflows/regression.yml` | Runs offline tests and fixture-based gate checks on GitHub Actions. |

The classifier supports `billing`, `technical`, `account`, and `general`.
Although classifications and golden examples include summaries, the evaluator
currently measures only category correctness. Summary quality is not scored or
stored in result reports.

## Data Provenance

The 40-example golden dataset was produced through AI-assisted generation and
reviewed by the repository author. This records the dataset's generation and
review process; it does not claim that every example was independently
verified beyond that process.

The two few-shot examples shared by the v1 and v2 prompts were AI-generated
and reviewed by the repository author. They are synthetic, do not contain real
customer communications, and are separate from the golden evaluation dataset.

## Prerequisites

- Python 3.11 is recommended and is the version used by GitHub Actions.
- An OpenAI API key is required only for live evaluation.
- Network access and an OpenAI account with available usage are required for
  live evaluation.

The type syntax requires Python 3.10 or newer, but CI currently verifies only
Python 3.11.

## Installation

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` contains both runtime dependencies and `pytest`, which is a
development dependency used by CI. Dependency versions are bounded but not
locked to an exact reproducible environment.

## Configuration

Copy the placeholder environment file and set your own key:

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=your-api-key
```

`classifier.py` loads `.env` through `python-dotenv`, and the OpenAI SDK reads
`OPENAI_API_KEY`. The local `.env` file is ignored by Git. Do not commit API
keys or put a real key in `.env.example`.

No API key is needed to compare committed reports, run unit tests, or exercise
the committed fixtures.

## Evaluate A Prompt

Live evaluation sends all 40 golden emails to OpenAI one at a time. It can
incur cost and is subject to network failures, rate limits, provider data
handling, and model variability.

Run the default v1 prompt:

```bash
python eval.py
```

Run v2 explicitly:

```bash
python eval.py --prompt-version v2
```

The selected value maps to `prompts/<version>.yaml` and is passed to both the
evaluation and report writer. Output is written to
`results/results_<version>.json`; an existing file at that path is overwritten.

Run the command from the repository root because dataset, prompt, and output
paths are currently relative to the working directory. Prompt versions are not
restricted by argparse, so the corresponding YAML file must exist.

## Compare Baseline And Candidate

Comparing committed reports is entirely offline:

```bash
python compare.py \
  baselines/approved_v1.jsonl \
  results/results_v2.json
```

The comparison requires matching example IDs and expected categories. For each
ID it reports:

- A regression when the baseline was correct and the candidate is incorrect.
- An improvement when the baseline was incorrect and the candidate is correct.
- No transition when both reports have the same correctness outcome.

Without strict mode, regressions are reported as warnings and the command exits
successfully:

```bash
python compare.py \
  baselines/approved_v1.jsonl \
  results/results_v2.json
```

Use strict mode for an enforceable regression gate:

```bash
python compare.py \
  baselines/approved_v1.jsonl \
  results/results_v2.json \
  --fail-on-regression
```

For the committed v1/v2 experiment, strict mode exits with code `1` because
example `033` regressed even though candidate accuracy increased.

One baseline can be compared with multiple candidates:

```bash
python compare.py baseline.json candidate-a.json candidate-b.json
```

### Exit Codes

| Code | Meaning |
| ---: | --- |
| `0` | Comparison succeeded. This also applies when regressions are reported without `--fail-on-regression`. |
| `1` | At least one regression was detected and strict mode was enabled. |
| `2` | Arguments, report data, files, or another operational input were invalid. |

`compare.py` writes a JSON representation followed by a human-readable report
to standard output. Its output stream is therefore not a JSON-only interface.

## Offline Tests

The automated tests do not require `OPENAI_API_KEY` and do not make OpenAI API
calls. The evaluation CLI tests mock dataset loading, model evaluation, and
result persistence.

Run the full test suite with pytest:

```bash
python -m pytest -q
```

The tests are also compatible with standard-library discovery:

```bash
python -m unittest discover -v
```

The approved-baseline tests check that the v1 report covers the golden dataset,
contains consistent outcomes, and has the expected prompt version. The v2
artifact is not currently covered by an equivalent integrity test.

## Offline Fixture Examples

The small reports in `tests/fixtures/` exercise gate behavior without a model
or API key.

Passing candidate, expected exit code `0`:

```bash
python compare.py \
  tests/fixtures/baseline.json \
  tests/fixtures/candidate_pass.json \
  --fail-on-regression
```

Regressing candidate in strict mode, expected exit code `1`:

```bash
python compare.py \
  tests/fixtures/baseline.json \
  tests/fixtures/candidate_fail.json \
  --fail-on-regression
```

Mismatched IDs, expected exit code `2`:

```bash
python compare.py \
  tests/fixtures/baseline.json \
  tests/fixtures/candidate_mismatched_ids.json \
  --fail-on-regression
```

These fixtures are separate from the 40-example v1/v2 experiment.

## GitHub Actions

`.github/workflows/regression.yml` runs on pushes and pull requests targeting
`main`. The workflow:

1. Uses Python 3.11.
2. Installs `requirements.txt`.
3. Runs the complete pytest suite.
4. Checks a passing fixture in strict mode.
5. Verifies that a regressing fixture exits with code `1`.
6. Verifies that invalid fixture input exits with code `2` rather than being
   misreported as a model regression.

CI is intentionally offline. It does not require an OpenAI key, run `eval.py`,
call an LLM, compare the real v2 report, publish a package, or deploy anything.
There is currently no continuous-deployment workflow.

## Current Limitations

- Live evaluation uses the hardcoded `gpt-4o-mini` model with no CLI control
  for model, temperature, seed, timeout, retries, or concurrency.
- Result reports do not record model configuration, timestamps, prompt hashes,
  dependency versions, or dataset revisions.
- Model outputs can vary between runs, so committed results are experiment
  artifacts rather than guaranteed reproducible outputs.
- `compare.py` trusts the report's declared accuracy instead of recomputing it
  and does not validate every optional report field.
- Evaluation prints the first input email and each outcome. Avoid using
  sensitive datasets where terminal or CI logs are retained.
- Summary quality is not evaluated.
- Generated result files are not automatically distinguished from curated,
  committed experiment artifacts.

## Security And Data Handling

Treat live inputs as data sent to an external provider. Review OpenAI's current
data-handling terms before evaluating confidential or regulated content. Keep
credentials in the ignored `.env` file or another secret manager, never in
source, prompts, datasets, reports, shell history, or CI configuration.

The dataset and prompt-example provenance is documented above. Before release,
scan all reachable Git history with a dedicated secret scanner; deleting a
secret from the latest revision does not remove it from history. For example,
Docker users can run a pinned Gitleaks release in read-only mode:

```bash
docker run --rm \
  -v "$PWD:/repo:ro" \
  ghcr.io/gitleaks/gitleaks:v8.30.1 \
  git --redact --verbose --log-opts="--all" /repo
```

Investigate each finding rather than automatically allowlisting it. Revoke or
rotate any real credential before cleaning it from history.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
