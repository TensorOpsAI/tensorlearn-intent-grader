import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import grade

ROOT = Path(__file__).resolve().parents[1]
GOOD = (ROOT/'fixtures/passing-intent.md').read_text()
CLAUDE = 'Read @intent.md before implementing.\n'
SHA = 'a'*40
runner = types.ModuleType('runner_test')
exec((ROOT/'grade.py').read_text().split("if __name__ == '__main__':")[0]
     + (ROOT/'runner.py').read_text().split("if __name__ == '__main__':")[0], runner.__dict__)

class GradingTests(unittest.TestCase):
    def test_passing_document(self):
        score, checks = grade.report(GOOD, CLAUDE, SHA, SHA)
        self.assertEqual(len(checks), 20)
        self.assertEqual(score['score'], 100, checks)
        self.assertEqual(score['gates']['tests'], {'total':20,'passed':20})

    def test_missing_contract_cannot_pass(self):
        checks = grade.check(GOOD.split('```')[0], CLAUDE)
        self.assertLessEqual(sum(c['passed'] for c in checks)*5, 15)

    def test_forged_expected_is_recomputed(self):
        bad = GOOD.replace('"error": "row-limit"', '"error": "everything-passed"')
        checks = grade.check(bad, CLAUDE)
        self.assertFalse(checks[12]['passed'])
        self.assertFalse(checks[19]['passed'])

    def test_placeholders_and_loader_code_fences(self):
        checks = grade.check(GOOD+'\nTODO\n', '```\n@intent.md\n```')
        self.assertFalse(checks[1]['passed'])
        self.assertFalse(checks[2]['passed'])

    def test_duplicate_keys_fail_contract(self):
        checks = grade.check(GOOD.replace('"schema": 1', '"schema": 1, "schema": 1'), CLAUDE)
        self.assertFalse(checks[3]['passed'])

    def test_incorrect_contract_types_do_not_crash(self):
        for key in ['requirements','acceptance_cases']:
            before, payload = GOOD.split('```json\n')
            c = json.loads(payload.split('```')[0]); c[key] = None
            self.assertLess(sum(x['passed'] for x in grade.check(before+'```json\n'+json.dumps(c)+'\n```\n',CLAUDE)),20)

    def test_csv_validation(self):
        for raw, error in [('', 'unknown-column'), ('title,title\na,b\n','unknown-column'),
                           ('title\na,b\n','unknown-column'), ('title\n"unterminated','unknown-column'),
                           ('title\n"  "\n','empty-title')]:
            self.assertEqual(grade.predict({'csv':raw})[0], {'error':error})
        self.assertEqual(grade.predict({'csv':'title,priority\n X , \n'})[0],
                         {'tickets':[{'title':'X','priority':'normal'}]})

    def test_row_limit_precedes_values(self):
        self.assertEqual(grade.predict({'csv':'title\n""\n','repeat':101})[0], {'error':'row-limit'})

    def test_bad_repeat_is_rejected(self):
        for repeat in [True,0,102,'101']:
            with self.assertRaises(ValueError):
                grade.predict({'csv':'title\na\n','repeat':repeat})

    def test_file_boundaries(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'intent.md'
            for data in [b'x'*(grade.MAX_BYTES+1),b'\xff']:
                path.write_bytes(data)
                with self.assertRaises(ValueError): grade.read_document(path)
            path.unlink(); path.symlink_to(ROOT/'fixtures/passing-intent.md')
            with self.assertRaises(ValueError): grade.read_document(path)

class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.repo='sample/fork'
        self.files={'intent.md':GOOD, 'CLAUDE.md':CLAUDE,
                    '.github/workflows/grade.yml':runner.caller_workflow(SHA)}
        self.blobs={}
        self.tree=[]
        for name,text in self.files.items():
            data=text.encode(); sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            self.tree.append({'path':name,'type':'blob','mode':'100644','sha':sha,'size':len(data)})
            self.blobs[sha]={'encoding':'base64','content':base64.b64encode(data).decode()}
        self.manifest={'CLAUDE.md':self.tree[1]['sha']}
        self.pull={'number':7,'state':'open','merged_at':None,
                     'base':{'ref':'main','repo':{'full_name':self.repo}},
                     'head':{'sha':SHA,'repo':{'full_name':self.repo}}}
    def api(self,path):
        if '/git/trees/' in path:return {'tree':self.tree,'truncated':False}
        if '/git/blobs/' in path:return self.blobs[path.rsplit('/',1)[1]]
        if '/pulls/7' in path:return self.pull
        raise AssertionError(path)
    def read(self):
        with patch.object(runner,'api',self.api):
            return runner.remote_documents(self.repo,SHA,SHA,self.manifest,7)
    def test_open_pr_immutable_documents(self): self.assertEqual(self.read(),(GOOD,CLAUDE))
    def test_closed_pr_rejected(self):
        self.pull['state']='closed'
        with self.assertRaises(ValueError):self.read()
    def test_changed_starter_rejected(self):
        self.manifest['CLAUDE.md']='b'*40
        with self.assertRaises(ValueError):self.read()
    def test_extra_file_rejected(self):
        self.tree.append({'path':'evil.py','type':'blob','mode':'100644'})
        with self.assertRaises(ValueError):self.read()
    def test_symlink_rejected(self):
        self.tree[0]['mode']='120000'
        with self.assertRaises(ValueError):self.read()
    def test_changed_pr_head_rejected(self):
        self.pull['head']['sha']='c'*40
        with self.assertRaises(ValueError):self.read()
    def test_upstream_pr_rejected(self):
        self.pull['base']['repo']['full_name']='upstream/starter'
        with self.assertRaises(ValueError):self.read()
    def test_foreign_pr_head_rejected(self):
        self.pull['head']['repo']['full_name']='someone/another-fork'
        with self.assertRaises(ValueError):self.read()
    def test_wrong_pr_number_rejected(self):
        self.pull['number']=8
        with self.assertRaises(ValueError):self.read()
    def test_network_failure_does_not_become_grade(self):
        with patch.object(runner,'api',side_effect=RuntimeError('transport')):
            with self.assertRaises(RuntimeError):runner.remote_documents(self.repo,SHA,SHA,self.manifest,7)

if __name__=='__main__': unittest.main()
