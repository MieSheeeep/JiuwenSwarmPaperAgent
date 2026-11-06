# Parallel upgrade execution amendment

This controller changes operational scheduling only. It retains the frozen
conditions, models, prompts, task files, scoring and context selections. It must
be used after the original sequential process has stopped at a condition boundary
and after an audited protocol amendment updates the stop-check source hash.

Run a read-only plan first:

```powershell
python -m research.parallel_upgrade --run-dir output/review_upgrade_20261106 --workers 3 --dry-run
```

After confirming the original process is stopped, leave root `STOP_REQUESTED`
present and run the same command without `--dry-run`. The controller launches a
validation-only subprocess against the root's original full grid. The existing
`execute_grid` checks persisted prompts, result hashes, contexts and provenance
before honoring the stop flag. No new condition may start in this validation.
The controller refuses pending requests, unapproved unknown usage, partial paid
conditions and incomplete existing external judgments. The recharge continuation
amendment permits only explicitly approved historical root transport failures in
`admission_reserves.json`. Each entry binds the exact request and call row hashes
and holds at least 10,000 tokens (or the larger original request reservation).
The original call remains `status: unknown` with null provider usage. These holds
are admission accounting, never measured usage or evidence of free calls. Only
those approved root calls are exempt from the paid-partial-condition guard.
Uncertain invocation errors and every new unknown child call still fail closed.

The remaining rows are grouped by `(kind, task_id)`. Groups are sorted by descending
pending cost, then stable task identity, and assigned greedily to the least-loaded
worker, with worker index resolving ties. A synthetic baseline row has cost 1;
a reflection row or external answer plus judge has cost 2. Every remaining row
of a task belongs to one process. No scores affect assignment. Frozen grid order
is retained within each worker.

Three processes use separate `segments/worker_i` directories and durable ledgers.
For a subsequent approved round, `--segments-name segments_round2` selects a new
single directory beneath the root. Only letters, digits, underscores and hyphens
are accepted; paths and traversal are rejected. Existing segment directories are
never reused. Archive the previous root `parallel_assignment.json` before the
next launch so its historical assignment remains available.
Each receives a byte copy of the initial selection cache, preserving previously
selected contexts. No root paid-call ledger is copied. Each child references the
root synthetic dataset and normalized `external_protocol/tasks.json`; external
data is not downloaded. DenseEncoder uses existing pinned local weights, four
CPU threads and the frozen identity. Credentials are read only inside explicitly
launched worker entry points; imports, planning and tests never read them.
Windows workers and the validation subprocess use `CREATE_NO_WINDOW`. Logs remain
in the run directory and contain no intentional credential output.

The global cap remains the root protocol cap. The controller subtracts validated
prior measured usage, all explicit unknown-spend holds and a 150,000-token writing
reserve, then divides the remainder by
pending cost using integer largest-remainder allocation. Child caps sum to at
most that remainder. Each existing executor also reserves 150,000 tokens inside
its assigned cap; this is deliberately conservative. Empty or too-small children
are not launched. Their pending rows may be resumed sequentially after merge.
Provider usage exceeding a cap is detected and reported; the controller does not
claim it can reverse an already billed provider overrun.

Root `parallel_assignment.json` records the root protocol and controller hashes,
source hashes, allocation, completed IDs and exact child grids. Child assignment
records and the root plan additionally bind the SHA-256 of
`admission_reserves.json` when present. Worker entry and merge revalidate that
binding; deleting, adding or editing the registry after assignment is rejected.
The plan reports `prior_known_usage`, `reserved_unknown_tokens` and
`prior_admission_usage` separately. Child assignment
records are separate from each child's protocol. Child protocols retain the root
scientific settings while replacing `token_limit` and setting `max_calls=6000`.
The original process must remain stopped throughout execution.

During execution, the controller reads LF-terminated snapshot records only; an
unfinished final JSONL line is ignored until complete, while malformed complete
lines fail closed. Root summary and run state aggregate prior and child evidence
without merging active ledgers. State is `parallel_running` or
`parallel_stopping`, with `active_workers` and `segmentcounts`. Normal in-flight
requests do not constitute unknown spend. An unknown response, uncertain
invocation or exited/stopped worker with an unresolved request writes
`STOP_REQUESTED` to every child; outstanding paid calls finish and workers stop
before their next condition. No automatic retry is performed.

When all children end, the controller validates source records and allocations,
then appends only previously unseen IDs to root ledgers. Existing bytes are never
truncated. Conflicting duplicate paid IDs or result IDs are rejected. Duplicate
selection keys must match every scientific field, including text and record IDs;
only selection timing/hash differences are tolerated, keeping the first source
record and hash. Per-row timing remains unchanged. Repeating a merge is
idempotent. `segment_merge_manifest.json` records each source file hash, root
protocol hash, controller source hash, actual usage and cap.
The manifest separates `actual_total_tokens`, `reserved_unknown_tokens` and
`admission_total_tokens`; cap checks use their conservative admission total.

The original full grid is used to recompute padded summaries with combined judge
metadata. Reports, matched analysis and claim outputs are regenerated after merge.
Summary resource `total_tokens` remains measured provider usage, while
`reserved_unknown_tokens`, `admission_total_tokens` and
`unreserved_unknown_usage_calls` expose admission holds and remaining blockers.
`answer_conditions_complete` reports full answer and external-judge completion
independently of billing reconciliation. Raw unknown usage keeps
`evaluation_complete` false even when every answer condition has finished.
If anything requires reconciliation, segment files remain the durable evidence;
resolve it before another launch. Existing segment directories are never
implicitly overwritten or reused. Root `STOP_REQUESTED` is retained so a later
sequential resume is an explicit operator action.
