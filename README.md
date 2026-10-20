# Intent document checker

Public, fictional training material for [the intent.md starter](https://github.com/TensorOpsAI/tensorlearn-intent-lab).
The reusable workflow reads immutable GitHub blobs, checks the starter manifest,
requires an open same-repository PR targeting main, and grades intent.md as data.
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
An invalid file tree/encoding/size/PR identity is zero with status `invalid`. GitHub API or
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
sent to the server. Remote source/PR tests mock the GitHub boundary; they do not
prove actual GitHub permissions or server ingestion.

`build_workflow.py` embeds the trusted checker and manifest directly into the
workflow. The workflow has a single job and a pinned artifact-upload action. Its
caller pins this repository's full commit SHA and supplies that same SHA as metadata;
the platform must independently verify the referenced workflow revision and artifact.
Never trust an arbitrary caller-supplied revision as proof of grader identity.

## Rehearsal checklist

1. Prepare the exercise record with immutable starter/checker revisions, `intent-md`,
   `intent-grade`, `intent-score`, and 100 points. Confirm the deployed platform
   supports approved public repositories and `pull_request` scoring evidence, and
   serves client v0.5.2 or later. These changes must be deployed before this works.
2. Enroll one test learner. They fork the shared starter and install the GitHub App
   on their exercise repository through the lab page. No per-student instructor
   repository setup or approval is needed for a public starter fork. Verify webhook
   and sweep delivery, configure the grading allowance, then launch.
3. Enable Actions in the fork. Connect Claude Code using the lab's `--code` command,
   and use `/load` from that fork to prove write control and connect it. Write intent.md
   on a solution branch and push it.
4. Open a PR inside the learner fork, targeting its main. Opening, reopening or
   updating the PR starts checks. The grader uses `github.event.pull_request.head.sha`,
   not `github.sha` (the synthetic merge preview for PR events). The PR remains open.
5. Inspect the artifact and then `/submit` the exact pushed head. An earlier advisory
   run may be reprocessed by the server sweep; the check itself creates no attempt.
6. Use `/check` and the website to verify the same learner, PR head, and official
   score. A new answer requires another commit/push and explicit submission.
7. Repeat with complete and incomplete documents. Verify an upstream-targeting PR
   is rejected, and check/result replays do not duplicate the official score.

Tests mock the GitHub boundary and do not prove production permissions. Full learner
Claude onboarding, App delivery and a saved official result must be observed during
rehearsal; do not claim them from unit tests or from a green Actions check. Customer
workshop IDs, accounts, and credentials stay outside these public repositories.

See [GitHub's PR event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)
for the distinction between the PR head and the synthetic merge commit.
