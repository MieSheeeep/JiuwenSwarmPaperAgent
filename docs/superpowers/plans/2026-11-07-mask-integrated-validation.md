# Mask-integrated validation: frozen research plan

**Goal:** Produce a new empirical/methods paper on selecting fixed linear prediction pipelines when the future rate of missing input values is uncertain. No digits/QA results or predictions are used.

**Architecture:** A new local study adapter runs the existing eleven-stage workflow, with a separate profile, source-derived equations/plots/tables and Flash-only authoring. Experiments and audits use CPU, not LLM answers. Prior paperreview feedback is read as fallible feedback, not as instructions or a target score.

**Tech stack:** Existing Python 3.12/NumPy/scikit-learn environment, UCI raw files, Ridge/HistGradientBoosting/KNNImputer, Matplotlib and LaTeX. Flash authoring ceiling: 100,000 tokens and 16 calls.

## Question and fixed design

Does integrating validation error over possible missing masks offer a useful way to select a linear predictor for uncertain missingness rates, compared with clean validation and finite-mask validation? This is an application of standard expected squared-loss algebra, related to dropout results; neither the quadratic identity nor model selection under missingness shift is claimed to be new.

- Datasets: UCI red wine quality (1599 x 11), white wine quality (4898 x 11), airfoil self-noise (1503 x 5), yacht hydrodynamics (308 x 6). These represent three families; the two wine subsets are related. Use all rows, disclose exact duplicate removal before splitting and retain source hashes. Targets are the supplied regression targets; no binarization.
- Splits: random feature-group splits with seeds 101/211/307/401/503, approximately 60% train, 20% complete validation, 20% test. Identical complete feature vectors stay in one partition; repeated splits overlap, and are not independent populations. Yacht/airfoil splitting still does not establish unseen experimental-configuration generalization.
- Training: independently mask 10% of training feature cells; all methods see the same masked matrix. Fit scaling statistics and mean/median fill values using only observed training entries. Standardize targets with training mean/SD. Hidden clean training cells are not used for fitting or imputation.
- Common primary candidate pool: mean or median fill, with or without an explicit indicator per feature; Ridge alpha 0.1/1/10. Twelve fitted candidates. All selection policies choose from exactly this pool, never from test labels.
- Fixed reference models: KNN-5 imputation plus Ridge(alpha=1), and native-missing HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=15,l2_regularization=1,early_stopping=False). They are context baselines outside the common linear selection pool, not evidence of fair tuning across model classes.
- Selection policies: clean validation; average validation MSE across rates 0.1/0.3/0.5 with 3 masks per rate; sampled worst-rate validation with 1, 3 or 9 masks per rate; exact analytic worst-rate validation over p in [0.1,0.5]; exact analytic maximization over only the same three rate points as a control. Include a known-p analytic selector as a privileged rate-aware diagnostic. Ties break by fixed candidate order.
- Each policy is frozen and saved before test labels are used. The known-p selector is permitted the declared missingness rate, not the test labels. The test-label-informed best-in-pool oracle is only an evaluation lower bound and is not deployable.
- Primary evaluation: nine common test-mask realizations per independent-MCAR condition p=0.1/0.3/0.5, for every linear and nonlinear method; include p=0 as a clean diagnostic. Report sqrt(mean normalized squared loss), regret in normalized MSE relative to the common-pool oracle, selected candidate identities and validation selection time. Exact expected losses for the affine pool are a separate diagnostic, not silently compared to sampled nonlinear-reference losses.
- Secondary stress tests: correlated row/block deletion at nominal p=0.3, and anchor-dependent MAR-like deletion at nominal p=0.3, three shared mask realizations. These deliberately violate independent MCAR assumptions. Keep feature 0 observed in the MAR-like mechanism; probability for other cells is clip(0.3*(0.5+sigmoid(anchor z)),0,0.95). The blocked mechanism jointly hides all features on selected rows. Report actual missing fractions.
- No outcome of the experiments determines whether a dataset, split, rate or policy is reported. There is no requirement that the analytic rule win.
- Variability: show per-dataset results and split dispersion. For the predeclared analytic-vs-clean comparison under p=0.5, report a conditional paired bootstrap interval (1000 draws) that clusters original row IDs across repeated test memberships. Fixed models/splits; no retraining or selection inside bootstrap; no universal or familywise significance claim.

## Exact identity and verification

For standardized complete x, fixed affine predictor coefficients a, intercept b, fixed fill f and missing-indicator coefficients c (zero when unused), define d_j=a_j(f_j-x_j)+c_j and e=b+a^T x-y. With independent Bernoulli(p) missing indicators,

`E[(prediction-y)^2 | x,y] = (e + p sum_j d_j)^2 + p(1-p) sum_j d_j^2`.

The validation mean is quadratic in p. Its maximum on the fixed interval is attained at an endpoint or an interior stationary point when the quadratic is concave. Check this identity by enumerating all masks for tiny examples; include a case where the interior maximum exceeds both endpoints. The guarantee is exact integration under the specified finite-row independent-mask model, not a population generalization or distributionally robust guarantee.

## Implementation and execution

1. Add hand-computable tests for mask integration, indicator handling, interior maxima, candidate selection not accessing test losses, and source/prediction tamper rejection.
2. Implement `research/workflow/missingness_study.py` with source downloads, deduplication, frozen splits, affine candidate fits and exact risk, selection policies saved before held-out scoring, reference predictions and immutable raw arrays.
3. Implement reporting with all fixed conditions, conditional clustered bootstrap, source-derived quantitative charts and a compact table. Store all rows and per-row errors for audit.
4. Implement a study-specific profile and CLI using the shared Workflow, skill loader, ledger and Flash-only backend. Do not reuse digits prompts, score definitions or QA replay.
5. Commit this plan and experiment code before viewing held-out performance. Run a development-only pilot, execute all data/split cells and replay primary affine predictions and metric aggregation. Do not alter scientific settings after observing outcomes.
6. Generate a full paper from compact new evidence, include the identity and its short proof, verify every formula/definition and both positive and negative findings, render all PDF pages and record any human interventions. Keep the private paperreview link/token out of git/public reports.

Local commands:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p test_missingness_study.py
.venv/Scripts/python.exe scripts/run_missingness_study.py --project output/framework_missingness_20261107 --enable-model
```

The user authorized a new easy-to-run topic after discussing missing-data experiments and reported the previous automated ICLR score as 4.4. No external upload, venue selection or score improvement is claimed by this plan.
