"""GitHub runner entrypoint; fetch only immutable blobs, never checkout candidate code."""
import base64
import hashlib
import os
import urllib.request


def api(path):
    req = urllib.request.Request('https://api.github.com/' + path, headers={
        'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(1048577)
        if len(raw) > 1048576:
            raise RuntimeError('GitHub response limit')
        return json.loads(raw)


def caller_workflow(sha):
    return ('name: Check intent submission\non:\n  push:\n    branches: [main]\n'
            'permissions:\n  contents: read\n  pull-requests: read\njobs:\n  grade:\n'
            '    uses: TensorOpsAI/tensorlearn-intent-grader/.github/workflows/grade.yml@' + sha + '\n'
            '    with:\n      grader-sha: ' + sha + '\n')


def remote_documents(repo, sha, grader_sha, manifest):
    tree = api(f'repos/{repo}/git/trees/{sha}?recursive=1')
    if tree.get('truncated') or len(tree.get('tree', [])) > 100:
        raise ValueError('submission tree limit')
    blobs = {item['path']: item for item in tree['tree'] if item['type'] != 'tree'}
    allowed = set(manifest) | {'intent.md', '.github/workflows/grade.yml'}
    if set(blobs) != allowed:
        raise ValueError('only intent.md may change')
    for path, item in blobs.items():
        if item.get('mode') != '100644' or item.get('type') != 'blob':
            raise ValueError('regular files only')
        if path in manifest and item['sha'] != manifest[path]:
            raise ValueError('starter files changed')
    def read(path):
        item = blobs[path]
        if item.get('size', MAX_BYTES+1) > MAX_BYTES:
            raise ValueError('document limit')
        blob = api(f'repos/{repo}/git/blobs/{item["sha"]}')
        if blob.get('encoding') != 'base64':
            raise ValueError('unsupported blob')
        data = base64.b64decode(blob['content'])
        if len(data) > MAX_BYTES:
            raise ValueError('document limit')
        expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if expected != item['sha']:
            raise ValueError('blob identity mismatch')
        return data.decode('utf-8', errors='strict')
    if read('.github/workflows/grade.yml') != caller_workflow(grader_sha):
        raise ValueError('caller workflow changed')
    # Require a merged, same-repository PR whose merge produced this exact revision.
    pulls = api(f'repos/{repo}/commits/{sha}/pulls?per_page=100')
    if not any(p.get('merged_at') and p.get('merge_commit_sha') == sha
               and p.get('base', {}).get('ref') == 'main'
               and p.get('base', {}).get('repo', {}).get('full_name', '').lower() == repo.lower()
               and (p.get('head', {}).get('repo') or {}).get('full_name', '').lower() == repo.lower()
               for p in pulls):
        raise ValueError('no merged PR for this main commit')
    return read('intent.md'), read('CLAUDE.md')


def run():
    sha, grader_sha, repo = os.environ['SUBMISSION_SHA'], os.environ['GRADER_SHA'], os.environ['SUBMISSION_REPO']
    if not re.fullmatch('[a-f0-9]{40}', sha) or not re.fullmatch('[a-f0-9]{40}', grader_sha):
        raise RuntimeError('invalid immutable revision')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise RuntimeError('invalid repository')
    try:
        text, claude = remote_documents(repo, sha, grader_sha, MANIFEST)
        score, checks = report(text, claude, sha, grader_sha)
    except (ValueError, UnicodeError):
        score, checks = report('', '', sha, grader_sha, invalid=True)
    # Transport/API failures propagate and produce no fabricated score.
    Path('result').mkdir(exist_ok=True)
    Path('result/score.json').write_text(json.dumps(score) + '\n')
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
        summary.write(f'# Intent document: {score["score"]}/100 ({score["status"]})\n\n')
        if not checks:
            summary.write('Submission rejected: verify a merged PR, unchanged starter files, regular UTF-8 documents, and the size limit.\n')
        for item in checks:
            summary.write(('- PASS: ' if item['passed'] else '- NEEDS WORK: ') + item['check'] + '\n')
        summary.write('\nThis is a document contract score. Server ingestion is a separate check.\n')


if __name__ == '__main__':
    run()
