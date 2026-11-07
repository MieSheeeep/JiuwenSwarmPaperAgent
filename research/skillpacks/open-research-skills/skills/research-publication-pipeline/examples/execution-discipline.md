# Worked example: a correct experiment can reject a hypothesis

This fictional regression study illustrates decision-making, not scientific evidence.
The values below are explanatory placeholders, not outputs from an executed run.
It requires no downloads, private data, remote compute, or locked-test access.

## Request and current state

The user asks to continue an agreed development experiment comparing a residual
correction against a matched regression baseline. The current protocol specifies
group-held-out development folds, mean absolute error (MAE), the same tuning budget,
and a minimum relevant paired improvement of 0.02. The final test is sealed.

The next task is to verify the MAE implementation and then evaluate the registered
candidate on the permitted development outputs. It does not reopen the research
question or require installing Superpowers.

## Task and implementation checks

The task points to the existing protocol and candidate entry, the versioned prediction
file, and the metric code revision. A tiny synthetic known-answer case has targets
`[1, 3]` and predictions `[1, 5]`: expected MAE is `1.0`. The implementation currently
squares residuals, returning `2.0`; this is a metric bug, not evidence about the
candidate. A separate known-bad split fixture repeats a group across train and
development; the leakage guard should reject it specifically for that overlap.

After correcting the metric, observe that the known-answer and clean split checks
pass and that the contaminated split fails for the intended reason. If earlier
candidate rankings used the buggy metric, mark those observations invalid and use the
protocol-repair path before selecting a candidate. Do not compare corrected candidate
scores against an uncorrected baseline.

## Scientific comparison and review

Suppose the corrected matched comparison shows improvement `0.003` and an interval
spanning zero. The implementation checks passing does not meet the registered minimum
improvement. Record the full paired comparison and determine whether the result is
underpowered or a measured miss using the frozen uncertainty rule. Do not widen the
threshold, choose a favorable seed, or access the final test to resolve disappointment.

The contract review checks metric, folds, baseline parity, and actual outputs. The
scientific review checks scope, uncertainty, and whether the mechanism's predicted
slice supports its explanation. Record the observation in the existing iteration
ledger and narrow or refute the candidate claim as justified. Then follow the existing
mechanism-level revision limit, remaining budget, and registered alternatives.

If two misses kill this mechanism while another registered candidate and budget remain,
pivot to that candidate; do not announce route-level saturation. If the user requested
only the metric fix, stop after reporting the fix and its observed verification rather
than initiating the comparison.

## Resume and delivery checks

On resume, inspect the corrected code and output locators rather than trusting a
previous completion message. A missing prediction file makes the comparison
unverified. Report checks not executed as not run. Keep working decisions in the
project records; public code artifacts follow the existing curated-release allowlist.
