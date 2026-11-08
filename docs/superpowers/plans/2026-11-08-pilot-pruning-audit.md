# Pilot-pruning audit implementation and execution plan

Goal: run a fresh research project through literature-based idea review, registered CPU experiments, evidence-linked English writing and independent review. This is a workflow test, not an optimization of the previous missingness paper.

The user authorized a new paper. Prior discussion approved reviewing candidates before substantial experiments. The initial runtime API ceiling is 250,000 tokens; an optional request to increase it is pending and is not authorization. Continue only under the existing ceiling unless the user answers. Use configured Flash only; preserve all earlier projects.

## Admission so far

Three initial proposals were independently reviewed in two fresh contexts and none admitted. Revised C4 remains unadmitted. C5 received **admit_pilot only**, with novelty/significance scores 2/5; this is not endorsement of full-paper adequacy or ICLR novelty. The standard interval/futility machinery is established prior art. C5 originated from an operator code-audit lead, explicitly recorded. No experimental outcomes have been inspected.

Correct the generated C5's invented availability of real judge outputs: none exist in this run. The proposed real replay is CPU classification paired predictions, not unperformed novelty-judge evaluations. The downloaded novelty benchmark was only audited for candidate feasibility and is not an evaluated dataset in C5.

## Research question and scope

How do interval construction, decision rules and nonzero deferral costs jointly affect false pruning in automated **performance-improvement** pilots? This is a conditional decision-policy audit, not a claim that all scientific hypotheses must improve predictive accuracy.

Compare paired-normal and conservative joint Clopper–Pearson bounds, crossed with:

- legacy binary policy: reject when lower bound is nonpositive; otherwise go only when observed gain reaches delta;
- delta-binary: go when lower bound exceeds delta, otherwise reject;
- tri-state: go when lower exceeds delta, reject when upper is below delta, otherwise defer;
- always-go, always-reject and always-defer diagnostic policies;
- matched-random deferral of a binary policy at the tri-state policy's aggregate defer rate across a predeclared heterogeneous effect mixture.

Use strict boundaries; equality to delta is inconclusive for tri-state. Factor interval and decision changes rather than attributing their joint difference to one mechanism. No theoretical novelty or safety certificate beyond the explicitly stated classical fixed-look bound.

## Files and tasks

1. `tests/test_pilot_pruning_study.py`: failing tests for tiny multinomial enumeration, zero-discordance uncertainty, exact-bound coverage, boundary decisions, aggregate random-deferral control and saved-artifact tampering.
2. `research/workflow/pilot_pruning_study.py`: pure interval/policy functions; categorical probability integration; pinned public-data preparation; fixed classifiers; immutable prediction replay and source checking. No model credentials.
3. `research/workflow/pilot_pruning_reporting.py`: deterministic result summaries, all registered conditions, cost frontiers, real-replay scopes, vector plots and source-derived tables. No invented measurements.
4. `research/workflow/pilot_pruning_profile.py` and `scripts/run_pilot_pruning_study.py`: register the plugin in the existing eleven-stage workflow, include proposal/review costs, require a numerical-health pilot and a separate post-pilot admission decision before full experiments. Use the existing ledger and source-backed authoring. Failed review must remain failed; a compiled draft is not an accepted paper.

## Frozen proposed protocol (final machine-readable freeze precedes outcomes)

- Synthetic paired difference D in {-1,0,+1}, with mean gain g and discordance q: P(+1)=(q+g)/2, P(-1)=(q-g)/2, P(0)=1-q. Enumerate all valid count outcomes at each fixed n; probabilities are integrated numerically, not called new independent experiments.
- q in {0.05,0.1,0.2,0.4}; g in {-0.08,-0.04,0,0.01,0.02,0.04,0.08,0.16}, retain only |g|<=q. n in {16,32,64,128,256}; delta in {0,0.02,0.05}; alpha=0.05. Means equal to delta are boundary cases, not counted as useful/futile.
- Normal intervals are approximate. The exact-joint construction subtracts two marginal Clopper–Pearson intervals, each with error alpha/2. Fixed-look coverage follows a union bound; this is prior art. Separate fixed n values are not optional repeated looks.
- Mixtures (clarified before any full outcomes): equal-regime weight 1; futile-heavy gives weight 3 to gain < delta - 1e-12 and 1 otherwise; useful-heavy gives weight 3 to gain > delta + 1e-12 and 1 otherwise. Normalize across regimes. Boundary regimes remain in denominators and carry neither error direction. These are sensitivity mixtures, not inverse-distance weighting or estimated prevalence. Show all mixtures rather than choose the best one post hoc.
- Real datasets: breast cancer and wine from installed sklearn; UCI Spambase and MAGIC from original sources with raw hashes. Train fixed logistic, histogram gradient boosting and random forest models using train-only preprocessing. Seeds {68101,68102,68103}; stratified train/test 60/40. Fixed pairs: logistic vs dummy, HGB vs logistic, RF vs HGB. No tuning from test outcomes.
- Replay the empirical paired-correctness distribution as a **conditional finite-benchmark reference**, not population ground truth. Shared data/model fits create dependence; Monte Carlo replicates or count states do not increase the number of datasets.
- Deferral cost in {0.05,0.25,1}; false-GO cost in {0.25,1,4}; false-reject cost in {1,4,16}. Report automatic coverage and both error directions together; no benefit claim from deferring everything. Costs are illustrative decision units, not measured tokens or money.
- Pilot uses small synthetic integration checks plus Iris only for execution health, not final benchmark outcomes or positive-gain selection. Stop on numerical/provenance failure. An additional source-based reviewer may reject a full study despite a passing health pilot.

## Completion and limits

Freeze protocol, source hashes and parameters before final outcomes. Run appropriate tests and read-only replay checks. Write English prose from full measurements, with positive/null/negative outcomes. Review claim support and contribution separately, keep source-based editorial changes explicit, render all PDF pages, and never assert conference acceptance or an official score. No external upload is part of this new-run instruction.


## Execution amendments before and during this run

- User approved a total 1,000,000 runtime API tokens, including the prior candidate calls.
- User explicitly directed completing our own experiments and ending repeated novelty vetoes. This supersedes the earlier pilot-only/full-admission condition. The earlier candidate reviews remain unchanged and are not relabeled as endorsements. Numerical health still gates the full run.
- Main displays were fixed before final outcomes: delta=.02, equal mixture, all n curves and both intervals; tables n32/128/256 and four policies; cost heatmap all27 triples at n256/exact_joint. Complete conditions remain in CSV files.
- Core completed 48 fits, four public datasets,36 paired references and11,520 decision-probability rows. These rows are sensitivity/integration conditions, not independent scientific replications.
- A real restart failure exposed Unicode paragraph separators in valid JSONL source text. LF-only record parsing fixed the false unknown-spend diagnosis; the original ledger remained unchanged and all six prior calls were reconciled with known usage. A failing regression preceded the fix.
- Authoring and review are fallible. A reviewer suggested an incorrect all405 cost-cell claim despite a positive maximum loss; explicit operator corrections retain356 wins/49 losses for the affected synthetic useful3x exact-joint comparison. All original model drafts/reviews are preserved. No experiment outcomes were edited.
