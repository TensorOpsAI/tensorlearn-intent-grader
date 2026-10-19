# Intent document checker

Public, fictional training material for [the intent.md starter](https://github.com/TensorOpsAI/tensorlearn-intent-lab).
The reusable workflow reads immutable GitHub blobs, checks the starter manifest,
requires a merged same-repository PR into main, and grades intent.md as data.
It never checks out or executes participant code. No LLM, paid API or server secret
is needed. GitHub Actions billing and quotas follow the repository owner's plan.

## Score contract

Exercise key `intent-md`, job `intent-grade`, artifact `intent-score` containing only
`score.json`. Maximum 100 points: 20 checks worth 5 each. The exact published checks
are in `grade.py`: six substantive sections; no placeholders; Claude import; contract
identity/shape; allowed changes; protected paths; non-goals; columns; priority rules;
validation/preview constraints; verification commands; approval; correct example
outputs; seven example categories. A known passing fictional document is provided
in `fixtures/passing-intent.md` so the rubric is transparent.

A score measures this contract, not semantic writing quality or Claude's compliance.
An invalid file tree/encoding/size/merge is zero with status `invalid`. GitHub API or
transport failures fail the run without inventing a score. Protected files must
match `manifest.json`; intent.md is limited to a regular UTF-8 file of 24 KiB.
CSV cases are limited to 20, and repetition to 101 rows of a single-row input.
Only examples with correct expected results contribute category coverage.

## Local validation

Requires Python 3.11 or newer; no packages to install:

```sh
python3 -m unittest discover -s tests -v
python3 grade.py /path/to/student/fork
python3 build_workflow.py
git diff --check
```

Local CLI results are advisory: their revision fields are zero and they are never
sent to the server. Remote source/merge tests mock the GitHub boundary; they do not
prove actual GitHub permissions or server ingestion.

`build_workflow.py` embeds the trusted checker and manifest directly into the
workflow. The workflow has a single job and a pinned artifact-upload action. Its
caller pins this repository's full commit SHA and supplies that same SHA as metadata;
the platform must independently verify the referenced workflow revision and artifact.
Never trust an arbitrary caller-supplied revision as proof of grader identity.

## Rehearsal checklist

1. Prepare an exercise record with the immutable starter and checker revisions,
   `intent-md`, `intent-grade`, `intent-score`, and 100 points. Do not launch yet.
2. Resolve submission compatibility: the currently observed platform expects a
   private repository and explicit open-PR submission; the requested exercise uses
   a public personal fork and merge as submission. This repository does not change
   that platform behavior. No automatic official score is claimed until resolved.
3. Enroll the actual test learner and approve the exact repository through the
   platform. Check the required GitHub App installation and webhook/sweep setup.
4. Fork the starter into a different personal account; enable Actions. Open in
   Claude Code. Confirm the intent import and discuss a deliberately incomplete draft.
5. Launch only when setup is ready. Merge the learner's own solution PR. Confirm
   the Actions artifact contains the actual merged SHA and pinned grader SHA.
6. Confirm the platform shows that same learner, attempt, commit, and score.
   Improving the document should create a new submission, not overwrite history.
7. Repeat with a complete document. Verify a direct push is rejected by this
   checker, and a run replay does not duplicate the official score.

The full rehearsal remains unrun. No real learner enrollment, connection tokens,
App installation, or server writes are exercised by these unit tests. Customer
workshop IDs, accounts, and credentials stay outside these public repositories.
