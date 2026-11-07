# Digits reliability study implementation plan

**Goal:** Train new local classifiers, run a frozen corruption/rejection study, and produce an evidence-linked English paper using Flash. No previous QA evidence is reused.

**Architecture:** A separate registered digits experiment adapter runs under the existing eleven-stage Workflow. Local training and scoring are deterministic and do not call an LLM. A digits-specific profile loads the pinned research/writing skills, passes compact measured evidence to Flash, compiles source-derived plots/tables, and records actual review decisions.

**Tech stack:** Python 3.12, NumPy, SciPy, scikit-learn MLPClassifier, Matplotlib, existing Workflow/ModelGateway/openJiuwen, local LaTeX.

The user selected handwritten-digit robustness and abstention. This document fixes the experiment before any held-out evaluation. This is an exploratory empirical study, not a new algorithm claim or an ICLR acceptance claim.

## Frozen scientific protocol

- Data: sklearn bundled digits, 1797 8x8 images, pixels divided by 16. One stratified split, seed 20261107: 1077 training, 360 validation, 360 held-out. Verify counts from actual split, record original sample indices. No old QA files.
- Model: MLP 64 -> 64 -> 32 -> 10, ReLU hidden units, Adam, batch 64, learning rate 0.001, L2 alpha 0.0001, 200 fixed epochs, no early stopping or test selection. Five initialization seeds: 11, 23, 37, 51, 71.
- Training uses only training labels. Validation fits scalar temperature by NLL and determines confidence thresholds. No corruption-specific thresholds and no test-label parameter updates.
- Confidence rules: maximum softmax probability, temperature-scaled maximum probability, top-two logit margin, negative entropy. Always-answer comparator.
- Coverage targets: 0.8 primary and 0.9 secondary. Threshold is validation score quantile at 1-target, fixed before test scoring; test coverage is measured rather than forced.
- Test conditions: clean; clipped additive Gaussian noise sigma 0.15/0.30/0.45; independent pixel dropout probability 0.10/0.30/0.50. One predeclared realization per condition; the exact same corrupted inputs go to every model and confidence rule.
- Endpoints: realized coverage and accepted-sample error, with accepted counts; overall accuracy; confidence ranking AURC; NLL and 15-bin ECE for unscaled/scaled probabilities. Empty accepted set yields null risk, never zero.
- Primary question: does a clean-validation threshold transfer its intended coverage and error behavior under these corruptions? Report all conditions and both targets regardless of outcome. No universal guarantee or significance claim.
- Five models share the same data/test images. Report mean and sample standard deviation over initialization seeds as optimization variability, not independent datasets or confidence intervals. Corruptions preserve nominal labels but severe corruption may make images ambiguous.
- The local pilot trains briefly on training data and checks validation logits/probabilities and finite metrics, without touching held-out inputs. Final models start fresh at fixed epoch count.

## Implementation steps

1. Add `tests/test_digits_study.py`: probability/logit agreement, quantile behavior, empty-acceptance semantics, deterministic corruption and freeze/tamper rejection. Run failing tests before implementing.
2. Add `research/workflow/digits_study.py`: split, frozen protocol, model training/saving, validation-only calibration, full held-out matrix and independent artifact rescoring. Save weights and validation/test logits without pickled model objects.
3. Add `research/workflow/digits_reporting.py`: aggregate all saved rows, create quantitative figures and compact display tables; preserve all raw outputs and score definitions.
4. Add `research/workflow/digits_profile.py`: wire literature, question, design, implementation, pilot, experiment, analysis, writing, grounded review and export under the existing engine. Flash-only guard. Reuse skill loading and durable accounting, not QA prompts/answers or QA-specific replay.
5. Extend local PDF compilation with hash-checked optional plots and literal data tables. Existing QA rendering stays available.
6. Add `scripts/run_digits_study.py`: create a fresh project under `output/framework_digits_20261107`, record model/token ceilings, then run the actual workflow. Flash ceiling 100,000 tokens / 16 calls. Train on CPU with two BLAS threads; no GPU needed.
7. Verify the new adapter on hand-computable examples and saved outputs, execute the real study, inspect every generated PDF page, record failures/interventions and final review status, then commit source and the public run report. Raw data/weights/API ledgers stay local.

Commands:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p test_digits_study.py
.venv/Scripts/python.exe scripts/run_digits_study.py --project output/framework_digits_20261107 --enable-model
.venv/Scripts/python.exe -m unittest discover -s tests -p test_workflow*.py
```

The target is a new paper backed by newly trained models and newly measured results. If review does not accept it, deliver a visibly labelled draft and its findings rather than weakening the review gate. A package or external submission is not part of this run.
