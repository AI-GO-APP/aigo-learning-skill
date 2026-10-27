import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import builder_runtime as runtime
from learning_bootstrap import prepare,setup,upgrade
BASE='https://course.ai-go.app'
ROLE='11111111-1111-4111-8111-111111111111'

class BuilderDependencyTests(unittest.TestCase):
    def fake(self,root,version='1.74.0',name='aigo-builder'):
        (root/'scripts').mkdir(parents=True)
        (root/'SKILL.md').write_text('---\nname: '+name+'\n---\n')
        (root/'VERSION').write_text(version)
        (root/'scripts/aigo_learning_scope.py').write_text('# fake fixture')
    def test_wrong_skill_old_version_and_future_major_are_rejected(self):
        for version,name in [('1.73.0','aigo-builder'),('2.0.0','aigo-builder'),('1.74.0','aigo-learning')]:
            with self.subTest(version=version,name=name),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.fake(root,version,name)
                with self.assertRaises(ValueError):runtime.metadata(root)
    def test_explicit_invalid_dependency_does_not_silently_switch_to_global(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fake(root,'1.73.0')
            with mock.patch.dict(os.environ,{'AIGO_BUILDER_SKILL':str(root)}):
                with self.assertRaises(ValueError):runtime.resolve()
    def test_workspace_marker_preserves_existing_rules_and_claude_import_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'AGENTS.md').write_text('existing rules\n');(root/'CLAUDE.md').write_text('existing Claude rules\n')
            prepare(root);before=(root/'AGENTS.md').read_bytes();prepare(root)
            self.assertEqual((root/'AGENTS.md').read_bytes(),before)
            self.assertTrue(before.startswith(b'existing rules'))
            self.assertEqual((root/'CLAUDE.md').read_text().count('@AGENTS.md'),1)
    def test_migration_preserves_assignments_and_never_reads_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);setup(root,BASE,'student@example.test',ROLE)
            profile=root/'.aigo/learning.json';data=json.loads(profile.read_text());data['apps']={'practice':'22222222-2222-4222-8222-222222222222'};profile.write_text(json.dumps(data))
            secret=root/'.aigo/.env';secret.write_bytes(b'private-test-fixture')
            original=Path.read_text
            def read(path,*a,**k):
                if path==secret:raise AssertionError('credentials must not be inspected')
                return original(path,*a,**k)
            with mock.patch.object(Path,'read_text',read):result=upgrade(root)
            self.assertFalse(result['credentials_accessed'])
            self.assertEqual(json.loads(profile.read_text())['apps'],data['apps'])
            self.assertEqual(secret.read_bytes(),b'private-test-fixture')
    def test_course_prepare_inside_skill_is_refused(self):
        with self.assertRaises(ValueError):prepare(ROOT/'tmp/forbidden')

if __name__=='__main__':unittest.main()
