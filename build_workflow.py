"""Regenerate the trusted single-job workflow after checker changes."""
import json
from pathlib import Path
root = Path(__file__).parent
code = (root / 'grade.py').read_text().split("if __name__ == '__main__':")[0]
code += '\nMANIFEST = ' + repr(json.loads((root / 'manifest.json').read_text())) + '\n'
code += (root / 'runner.py').read_text()
yaml = '''name: Grade intent document
on:
  workflow_call:
    inputs:
      grader-sha:
        required: true
        type: string
permissions:
  contents: read
  pull-requests: read
  id-token: write
jobs:
  intent-grade:
    name: intent-grade
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - name: Read and check immutable documents
        shell: python
        env:
          GITHUB_TOKEN: ${{ github.token }}
          SUBMISSION_REPO: ${{ github.repository }}
          SUBMISSION_SHA: ${{ github.event.pull_request.head.sha }}
          SUBMISSION_PR: ${{ github.event.pull_request.number }}
          SUBMISSION_EVENT: ${{ github.event_name }}
          GRADER_SHA: ${{ inputs.grader-sha }}
        run: |
'''
yaml += ''.join(('          ' + line if line else '') + '\n' for line in code.splitlines())
yaml += '''      - name: Upload score
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: intent-score
          path: result/score.json
          if-no-files-found: error
          retention-days: 7
'''
yaml += '''      - name: Report score to TensorLearn
        continue-on-error: true
        shell: python
        run: |
'''
yaml += ''.join(('          ' + line if line else '') + '\n' for line in (root / 'report_score.py').read_text().splitlines())
(root / '.github/workflows/grade.yml').write_text(yaml)
