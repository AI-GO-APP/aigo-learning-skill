import copy,io,json,runpy,sys,tarfile,tempfile,types,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from learning_bootstrap import setup
import learning_scope as scope
ci=runpy.run_path(str(ROOT/'assets/hosted-ci.py'))
BASE='https://course.ai-go.app'; ROLE='11111111-1111-4111-8111-111111111111'
APP='22222222-2222-4222-8222-222222222222'; USER='33333333-3333-4333-8333-333333333333'

class BootstrapTests(unittest.TestCase):
    def test_creates_non_secret_workspace_without_platform_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'work'; result=setup(root,BASE,'student@example.test',ROLE)
            self.assertEqual(result['platform_operations'],0)
            self.assertIn('AIGO_PASSWORD=\n',(root/'.aigo/.env').read_text())
            self.assertEqual(json.loads((root/'.aigo/config.json').read_text())['apps'],{})
            self.assertTrue((root/'output/pdf').is_dir())
            self.assertIn('.aigo/',(root/'.gitignore').read_text())
    def test_existing_credentials_are_untouched_and_no_other_settings_written(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'.aigo').mkdir(); secret=root/'.aigo/.env';secret.write_bytes(b'private fixture')
            with self.assertRaises(ValueError): setup(root,BASE,'student@example.test',ROLE)
            self.assertEqual(secret.read_bytes(),b'private fixture')
            self.assertFalse((root/'.aigo/config.json').exists())
    def test_invalid_target_rejected_before_creating_workspace(self):
        for base,email,role in [('https://evil.test','student@example.test',ROLE),(BASE,'student\n@example.test',ROLE),(BASE,'student@example.test','unknown')]:
            with self.subTest(base=base,email=email),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'new'
                with self.assertRaises(ValueError): setup(root,base,email,role)
                self.assertFalse(root.exists())
    def test_existing_ignore_rules_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'.gitignore').write_text('custom-file\n')
            setup(root,BASE,'student@example.test',ROLE)
            self.assertIn('custom-file\n',(root/'.gitignore').read_text())

class HostedScopeTests(unittest.TestCase):
    def setUp(self):
        self.profile={'tenant_url':BASE,'student_email':'student@example.test','role_id':ROLE,'apps':{},
                      'hosted_apps':{'site':{'id':APP,'slug':'student-site','visibility':'public','public_approved':True}}}
        self.config={'base_url':BASE,'email':'student@example.test','apps':{'site':{'id':APP,'kind':'hosted'}}}
        self.me={'email':'student@example.test','id':USER}
        self.info={'id':APP,'slug':'student-site','created_by':USER,'visibility':'public','access_role_ids':[]}
    def target(self):return scope.check_local(self.profile,self.config,BASE,'site','hosted')
    def test_public_does_not_require_internal_role_but_does_not_claim_data_safety(self):
        result=scope.check_hosted_remote(self.target(),self.me,self.info)
        self.assertEqual(result['scope_check'],'passed');self.assertEqual(result['mutations'],0)
        self.assertFalse(result['server_authorization_verified']);self.assertFalse(result['anonymous_access_verified'])
    def test_public_without_approval_or_wrong_product_line_rejected(self):
        self.profile['hosted_apps']['site']['public_approved']=False
        with self.assertRaisesRegex(ValueError,'公開'):self.target()
        self.profile['hosted_apps']['site']['public_approved']=True;self.config['apps']['site']['kind']='custom'
        with self.assertRaises(ValueError):self.target()
    def test_other_owner_wrong_slug_visibility_or_roles_rejected(self):
        for key,value in [('created_by',ROLE),('slug','other-site'),('visibility','internal'),('access_role_ids',[ROLE]),('id',ROLE)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                scope.check_hosted_remote(self.target(),self.me,{**self.info,key:value})
    def test_internal_hosted_requires_dedicated_group(self):
        self.profile['hosted_apps']['site']['visibility']='internal';self.info['visibility']='internal'
        with self.assertRaises(ValueError):scope.check_hosted_remote(self.target(),self.me,self.info)
        self.info['access_role_ids']=[ROLE]
        self.assertEqual(scope.check_hosted_remote(self.target(),self.me,self.info)['scope_check'],'passed')
    def test_cli_checks_identity_then_only_the_exact_hosted_app(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'.aigo').mkdir()
            for name,body in [('config.json',self.config),('learning.json',self.profile)]:
                (root/'.aigo'/name).write_text(json.dumps(body))
            auth=types.SimpleNamespace(resolve_base_url=mock.Mock(return_value=BASE),get_token=mock.Mock(return_value='fake-test-token'))
            def response(body):return types.SimpleNamespace(raise_for_status=mock.Mock(),json=mock.Mock(return_value=body))
            http=types.SimpleNamespace(get=mock.Mock(side_effect=[response(self.me),response(self.info)]))
            with mock.patch.dict(sys.modules,{'aigo_auth':auth,'httpx':http}),mock.patch('sys.stdout',new_callable=io.StringIO) as out:
                self.assertEqual(scope.main(['--workspace',str(root),'--app','site','--kind','hosted']),0)
            self.assertEqual(http.get.call_args_list[1].args[0],BASE+'/api/v1/hosted-apps/'+APP)
            self.assertNotIn('fake-test-token',out.getvalue())

class HostedCiTests(unittest.TestCase):
    def fixture(self,root):
        (root/'Dockerfile').write_text('FROM node:22\nCOPY . .\n')
        (root/'VERSION').write_text('0.1.0\n');(root/'server.js').write_text('// fixture')
        cfg={'tenant_url':BASE,'app_id':APP,'public_url':'https://student-site.apps.ai-go.app','include':['Dockerfile','VERSION','server.js']}
        (root/'deploy.json').write_text(json.dumps(cfg));return cfg
    def test_tar_uses_only_declared_files_and_adds_exact_commit_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);cfg=self.fixture(root);(root/'.env').write_text('private fixture')
            payload=ci['tarball'](root,cfg,'a'*40)
            with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as archive:
                self.assertNotIn('.env',archive.getnames())
                self.assertEqual(json.loads(archive.extractfile('.aigo-build.json').read())['commit'],'a'*40)
    def test_escaping_and_secret_paths_refused(self):
        for name in ('../outside','.env','sub/private.key'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);cfg=self.fixture(root)
                if name!='../outside':
                    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('private fixture')
                cfg['include'].append(name)
                with self.assertRaises(ValueError):ci['source_files'](root,cfg)
    def test_deploy_requires_dedicated_token_before_network(self):
        with tempfile.TemporaryDirectory() as temp,mock.patch.dict('os.environ',{},clear=True),mock.patch.dict(sys.modules,{'httpx':types.SimpleNamespace()}):
            root=Path(temp);cfg=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'Actions secret'):ci['deploy'](root,cfg,'a'*40)

if __name__=='__main__':unittest.main()
