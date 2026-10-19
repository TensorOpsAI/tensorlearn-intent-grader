# Intent

## Goal
Let a support coordinator preview CSV tickets before approving any later import.

## Scope
Add src/import-tickets.mjs and tests/import-tickets.test.mjs only in a later implementation round. Exclude UI, database and network work.

## Constraints
Preserve src/tickets.mjs, .github/ and CLAUDE.md. Use no new dependencies or file writes. The function returns a preview only.

## Plan
First agree the contract, then parse the CSV with quoting, check the row limit before values, validate columns and values, and return a complete result or one error.

## Acceptance
Use the cases below to demonstrate valid inputs, defaults, quoted commas, and all specified failure codes. Return no partial results on failure.

## Verification
Run npm test and git diff --check after implementation. For now only write intent.md. Ask before implementation or any expansion of scope.

```json
{
  "schema": 1,
  "change": "ticket-csv-preview",
  "allowed_changes": [
    "src/import-tickets.mjs",
    "tests/import-tickets.test.mjs"
  ],
  "protected_paths": [
    "src/tickets.mjs",
    ".github/",
    "CLAUDE.md"
  ],
  "non_goals": [
    "ui",
    "database",
    "network"
  ],
  "requirements": {
    "columns": [
      "title",
      "priority"
    ],
    "default_priority": "normal",
    "valid_priorities": [
      "low",
      "normal",
      "urgent"
    ],
    "reject_unknown_columns": true,
    "reject_empty_title": true,
    "max_rows": 100,
    "side_effects": "preview-only"
  },
  "verification": [
    "npm test",
    "git diff --check"
  ],
  "approval": "ask-before-implementation",
  "acceptance_cases": [
    {
      "csv": "title,priority\nPrinter issue,urgent\n",
      "expected": {
        "tickets": [
          {
            "title": "Printer issue",
            "priority": "urgent"
          }
        ]
      }
    },
    {
      "csv": "title\nPrinter issue\n",
      "expected": {
        "tickets": [
          {
            "title": "Printer issue",
            "priority": "normal"
          }
        ]
      }
    },
    {
      "csv": "title,priority\n\"Printer, upstairs\",low\n",
      "expected": {
        "tickets": [
          {
            "title": "Printer, upstairs",
            "priority": "low"
          }
        ]
      }
    },
    {
      "csv": "title\n\"\"\n",
      "expected": {
        "error": "empty-title"
      }
    },
    {
      "csv": "title,owner\nPrinter,Ada\n",
      "expected": {
        "error": "unknown-column"
      }
    },
    {
      "csv": "title,priority\nPrinter,critical\n",
      "expected": {
        "error": "invalid-priority"
      }
    },
    {
      "csv": "title\nPrinter\n",
      "repeat": 101,
      "expected": {
        "error": "row-limit"
      }
    }
  ]
}
```
