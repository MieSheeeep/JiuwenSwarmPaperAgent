# Research execution discipline

Use this reference when an agreed research plan needs executable tasks, when resuming
implementation, or when Superpowers is also present. Apply only the steps needed to
resolve the current scientific decision. A source lookup or small prose edit does not
need a new plan, worktree, or review round.

This is an original research adaptation of workflow ideas described by
[Superpowers](https://github.com/obra/superpowers): clarify intent, plan bounded work,
investigate failures, and verify completion. It needs no Superpowers installation,
hooks, remote launcher, or additional public skill. This reference supplies guidance;
the existing project validator does not enforce every practice described here.

For a concrete metric-bug versus negative-result distinction, read the
[worked example](../examples/execution-discipline.md) when that distinction is unclear.

## Start from the existing contract

Read the active project and relevant records before asking for requirements again.
Reuse the current scope and authorization; ask only about consequential unresolved
choices. Map the next decision to an existing mode and record:

| Decision | Existing owner / record |
|---|---|
| Question, contribution lane, feasibility | `intake/intake.json` |
| Source acquisition and verification | `evidence/source-register.json` |
| Split, metric, controls, budget, final-test policy | `protocol/protocol.json` |
| Whether complexity is justified | `development/headroom.json` |
| Candidate, observations, failure, next decision | `development/iteration-ledger.json` |
| Supported scope and uncertainty | `claims/claim-register.json` |
| Terminal outcome and next deliverable | `handoff/handoff.json` |

Use the existing schema and evidence locators. Do not add invented fields to those
records or create a second authoritative experiment ledger. Temporary implementation
notes may link to them; runtime notes and execution traces stay out of the public
release tree under the existing release boundary.

## Make each task answer a decision

In the current working plan, capture the following for a nontrivial implementation or
analysis task. This is a writing aid, not a new required JSON schema:

- Decision and applicable protocol version.
- Inputs, data versions, independent unit, permitted split, and source locators.
- One bounded implementation change and the output artifacts it should create.
- Verification command or inspection, expected behavior, and meaningful failure case.
- Environment or dependency lock, resource budget, and any ungranted action needed.
- Where the observation will be recorded and which existing decision it can change.

Split work where outputs can be independently checked. Do not split a shared data
preprocessing or selection decision across concurrent writers. Keep the task size
proportional to the cost of discovering a wrong assumption.

## Separate implementation tests from scientific outcomes

For executable behavior, test known answers, input contracts, unit conversions,
independent-unit grouping, split separation, and deterministic transformations. A
known-bad fixture should fail for the intended reason; a clean fixture should pass.
For a reproduced code defect, observe the failure, repair its cause, then run the
relevant regression checks. Existing correct code need not be rewritten to recreate
a red-green sequence.

For a scientific hypothesis, register the endpoint, comparator, minimum relevant
effect, uncertainty method, controls, and falsifier before the comparison. A negative
scientific result can be a correctly executed experiment. Do not tune until a desired
finding becomes a passing test, change tolerances after observing results, or fabricate
an expected outcome for unseen data. Development checks use permitted development or
synthetic data; they do not inspect the locked test.

If a run fails, distinguish implementation error, environment failure, data limitation,
insufficient resolution, and a measured scientific miss. Use the existing
[controlled-development recovery order](protocol-headroom-and-development.md).
Only a diagnosed implementation defect calls for code repair; other outcomes use the
frozen revise, pivot, stop, or new-protocol rules.

## Verify in two passes

Before reporting a substantial task complete, use the current artifacts and run
evidence, not the implementer's summary alone:

1. **Contract and execution:** inspect the actual diff or method, input identity,
   split boundaries, comparator parity, verification output, and failed/not-run work.
   A rerun belongs within the existing resource authorization. If it cannot run,
   state the missing check rather than recording a pass.
2. **Scientific support:** check whether the result supports its proposed scope,
   mechanism, uncertainty unit, and limitations. Good code and a passing record
   validator do not establish a scientific finding. Narrow or refute claims when
   the evidence requires it.

One agent can perform both passes sequentially; label that as self-review. When
independent review or delegation is requested and supported, supply the reviewer with
the frozen question, protocol, source/output locators, and relevant implementation.
Keep the author's preferred conclusion out of the review brief. Multiple agents
examining the same evidence are not independent empirical replications.

If work is delegated, give each worker a bounded output, permitted inputs and tools,
and a disjoint write scope. A coordinator reconciles the actual results into the
canonical records. A Git worktree isolates code edits only: shared data, caches,
credentials, remote jobs, and locked-test access still need their own boundaries.
Unavailable delegation is not a reason to stop work that can be completed sequentially.

## Finish with a reconstructable handoff

Link the produced artifact to the actual input version, generating code revision,
configuration, environment, command, and observed result using existing evidence
locations. Where an underlying execution platform automatically captures provenance,
verify the links it exposes. Otherwise record the missing pieces explicitly; these
skills do not supply an automatic lineage database or portable compute backend.

Resume by checking the active protocol and newest real outputs. A prior task marked
done is not evidence that its files exist, its source is still current, or its result
applies to a changed protocol.

Run the existing validator for the boundary being crossed. Keep implementation
completion, scientific support, manuscript readiness, and external publication
separate. Preserve negative outcomes and budget exhaustion. Opening a PR, submitting
a benchmark, publishing data, or merging a branch follows the actual user scope;
finishing a task does not independently grant those actions.

## When Superpowers is installed too

Use its implementation planning, debugging, and code verification for bounded coding
tasks. Keep research decisions under this skill's protocol, candidate order, final-test
isolation, and claim rules. A software acceptance test cannot overwrite a scientific
falsifier, and a development-branch completion action cannot imply publication.

Avoid duplicate brainstorming when a valid charter exists. Keep one current plan and
one scientific record set. Skill discovery is task-scoped: load the relevant reference
or available specialist rather than every installed skill. Explain each constraint
with its reason and applicability; reserve hard gates for real contract boundaries.
