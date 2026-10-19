"""Document-only checker. Candidate content is parsed as data, never executed."""
import csv
import io
import json
import re
from pathlib import Path

MAX_BYTES = 24576
NAMES = ['Goal', 'Scope', 'Constraints', 'Plan', 'Acceptance', 'Verification']
CATEGORIES = ['explicit-priority', 'default-priority', 'quoted-comma', 'empty-title',
              'unknown-column', 'invalid-priority', 'row-limit']


def predict(case):
    if not isinstance(case, dict) or set(case) - {'csv', 'expected', 'repeat'}:
        raise ValueError('case shape')
    raw = case.get('csv')
    repeat = case.get('repeat', 1)
    if not isinstance(raw, str) or len(raw) > MAX_BYTES or type(repeat) is not int or not 1 <= repeat <= 101:
        raise ValueError('case limits')
    try:
        rows = list(csv.reader(io.StringIO(raw), strict=True))
    except csv.Error:
        return {'error': 'unknown-column'}, {'unknown-column'}
    if not rows:
        return {'error': 'unknown-column'}, {'unknown-column'}
    header, data = rows[0], rows[1:]
    if repeat != 1 and len(data) != 1:
        raise ValueError('repeat requires one data row')
    data = data * repeat
    if len(data) > 100:
        return {'error': 'row-limit'}, {'row-limit'}
    if ('title' not in header or len(set(header)) != len(header)
            or set(header) - {'title', 'priority'} or any(len(row) != len(header) for row in data)):
        return {'error': 'unknown-column'}, {'unknown-column'}
    tickets, tags = [], set()
    for row in data:
        values = dict(zip(header, (v.strip() for v in row)))
        if not values['title']:
            return {'error': 'empty-title'}, {'empty-title'}
        priority = values.get('priority', '')
        if priority and priority not in ['low', 'normal', 'urgent']:
            return {'error': 'invalid-priority'}, {'invalid-priority'}
        tags.add('explicit-priority' if priority else 'default-priority')
        if ',' in values['title']:
            tags.add('quoted-comma')
        tickets.append({'title': values['title'], 'priority': priority or 'normal'})
    return {'tickets': tickets}, tags


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def check(text, claude):
    prose = re.sub(r'^```[^\n]*\n.*?^```\s*$', '', text, flags=re.M | re.S)
    sections = re.findall(r'^## (Goal|Scope|Constraints|Plan|Acceptance|Verification)\s*\n(.*?)(?=^## |\Z)', prose, re.M | re.S)
    results = []
    def add(label, passed):
        results.append({'check': label, 'passed': bool(passed)})
    add('Six substantive sections', len(sections) == 6 and {s[0] for s in sections} == set(NAMES)
        and all(len(re.sub(r'\s+', ' ', s[1]).strip()) >= 30 for s in sections))
    add('No placeholders', not re.search(r'\b(TODO|TBD|FIXME)\b|<insert|\[your .+?\]', text, re.I))
    loader = re.sub(r'^```[^\n]*\n.*?^```\s*$', '', claude, flags=re.M | re.S)
    loader = re.sub(r'`[^`]*`', '', loader)
    add('Claude imports intent', bool(re.search(r'(?<!\S)@(?:\./)?intent\.md\b', loader)))
    blocks = re.findall(r'^```json\s*\n(.*?)^```\s*$', text, re.M | re.S)
    contract = {}
    try:
        if len(blocks) == 1:
            contract = json.loads(blocks[0], object_pairs_hook=no_duplicate_keys)
            if not isinstance(contract, dict):
                contract = {}
    except (ValueError, RecursionError):
        pass
    keys = {'schema','change','allowed_changes','protected_paths','non_goals','requirements','verification','approval','acceptance_cases'}
    add('Contract identity and shape', set(contract) == keys and type(contract.get('schema')) is int
        and contract['schema'] == 1 and contract.get('change') == 'ticket-csv-preview')
    add('Allowed changes', contract.get('allowed_changes') == ['src/import-tickets.mjs','tests/import-tickets.test.mjs'])
    add('Protected paths', contract.get('protected_paths') == ['src/tickets.mjs','.github/','CLAUDE.md'])
    add('Non-goals', contract.get('non_goals') == ['ui','database','network'])
    req = contract.get('requirements', {})
    if not isinstance(req, dict):
        req = {}
    add('CSV columns', req.get('columns') == ['title','priority'])
    add('Priority rules', req.get('default_priority') == 'normal' and req.get('valid_priorities') == ['low','normal','urgent'])
    add('Validation and preview constraints', req.get('reject_unknown_columns') is True
        and req.get('reject_empty_title') is True and type(req.get('max_rows')) is int and req['max_rows'] == 100
        and req.get('side_effects') == 'preview-only'
        and set(req) == {'columns','default_priority','valid_priorities','reject_unknown_columns','reject_empty_title','max_rows','side_effects'})
    add('Verification commands', contract.get('verification') == ['npm test','git diff --check'])
    add('Approval boundary', contract.get('approval') == 'ask-before-implementation')
    cases = contract.get('acceptance_cases', [])
    valid = isinstance(cases, list) and 1 <= len(cases) <= 20
    covered = set()
    if valid:
        for case in cases:
            try:
                expected, tags = predict(case)
                # JSON comparison distinguishes booleans from integers.
                correct = json.dumps(case.get('expected'), sort_keys=True) == json.dumps(expected, sort_keys=True)
                valid = valid and correct
                if correct:
                    covered.update(tags)
            except (ValueError, TypeError, RecursionError):
                valid = False
    add('All acceptance examples are correct', valid)
    for category in CATEGORIES:
        add('Example: ' + category, category in covered)
    return results


def report(text, claude, submission_sha, grader_sha, invalid=False):
    results = check(text, claude) if not invalid else []
    passed = sum(item['passed'] for item in results)
    score = passed * 5
    return {'schema': 1, 'exercise': 'intent-md', 'grader_sha': grader_sha,
            'submission_sha': submission_sha, 'status': 'invalid' if invalid else 'graded',
            'score': score, 'max': 100,
            'points': {'scope': 0, 'static': 0, 'tests': score, 'regression': 0},
            'gates': {'tests': {'total': 20, 'passed': passed}}}, results


def read_document(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('document must be a regular file no larger than 24 KiB')
    return path.read_bytes().decode('utf-8', errors='strict')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('submission', type=Path)
    args = p.parse_args()
    try:
        score, checks = report(read_document(args.submission / 'intent.md'),
                               read_document(args.submission / 'CLAUDE.md'), '0'*40, '0'*40)
    except (ValueError, OSError):
        score, checks = report('', '', '0'*40, '0'*40, invalid=True)
    print(json.dumps({'advisory_local_score': score, 'checks': checks}, indent=2))
