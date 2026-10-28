import contextlib,copy,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import learning_policy as policy
import learning_scope as scope
from learning_bootstrap import prepare,upgrade

USER='33333333-3333-4333-8333-333333333333'
OTHER='44444444-4444-4444-8444-444444444444'
ROLE='11111111-1111-4111-8111-111111111111'
APP='22222222-2222-4222-8222-222222222222'
SITE='55555555-5555-4555-8555-555555555555'
TABLE='66666666-6666-4666-8666-666666666666'

class OperationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.work=Path(self.temp.name)
        (self.work/'.aigo').mkdir()
        self.me={'id':USER,'email':'student@example.test','role_ids':[ROLE],'permissions':['builder.access']}
        self.profile={'tenant_url':'https://course.ai-go.app','student_email':'student@example.test','role_id':ROLE,
                      'apps':{'practice':APP},'hosted_apps':{'site':{'id':SITE,'slug':'demo-site','visibility':'public','public_approved':True}},'data_resources':{}}
        self.config={'base_url':'https://course.ai-go.app','email':'student@example.test','apps':{'practice':{'id':APP,'kind':'custom'},'site':{'id':SITE,'kind':'hosted','slug':'demo-site'}}}
        self.personal={'table_id':TABLE,'app':'practice','mode':'personal','source':'created','owner_user_id':USER,'operations':['read','create','update','delete','schema','reference']}
        self.shared={'table_id':TABLE,'app':'practice','mode':'shared','source':'assigned','owner_field':'owner_student_id','gate_verified':True,'operations':['read','create','update','delete','reference','schema']}
        self.write()
    def write(self):
        for name,data in [('learning.json',self.profile),('config.json',self.config)]:
            (self.work/'.aigo'/name).write_text(json.dumps(data),encoding='utf-8')
    def check(self,operation,**kwargs):return policy.check(self.work,'practice',operation,identity=self.me,table='biz_practice',**kwargs)
    def allow(self,shared=False):
        self.profile['data_resources']['biz_practice']=copy.deepcopy(self.shared if shared else self.personal);self.write()
    def test_management_operations_stop_before_context_or_credentials(self):
        with mock.patch.object(policy,'context',side_effect=AssertionError('must not access files')):
            for op in policy.FORBIDDEN:
                with self.subTest(operation=op),self.assertRaises(ValueError):self.check(op)
    def test_scope_adapter_does_not_start_builder_for_forbidden_operation(self):
        with mock.patch('subprocess.run') as run,contextlib.redirect_stdout(io.StringIO()):
            result=scope.main(['--workspace',str(self.work),'--app','practice','--operation','data_policy'])
            self.assertEqual(result,1);run.assert_not_called()
    def test_adapter_checks_table_before_invoking_builder(self):
        identity=self.work/'me.json';identity.write_text(json.dumps(self.me),encoding='utf-8')
        args=['--workspace',str(self.work),'--app','practice','--operation','read','--table','biz_practice','--identity-file',str(identity)]
        with mock.patch('subprocess.run') as run,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scope.main(args),1);run.assert_not_called()
        self.allow()
        with mock.patch('subprocess.run',return_value=mock.Mock(returncode=0)) as run:
            self.assertEqual(scope.main(args),0);self.assertEqual(run.call_count,1)
            self.assertEqual(run.call_args.args[0][-4:],['--app','practice','--kind','custom'])
    def test_empty_and_unknown_resource_lists_do_not_grant_access(self):
        for op in policy.DATA_OPERATIONS:
            with self.subTest(operation=op),self.assertRaises(ValueError):self.check(op)
    def test_registered_personal_table_allows_only_owner(self):
        self.allow()
        for op in policy.DATA_OPERATIONS:self.assertEqual(self.check(op)['operation_check'],'passed')
        self.profile['data_resources']['biz_practice']['owner_user_id']=OTHER;self.write()
        with self.assertRaises(ValueError):self.check('read')
    def test_wrong_identity_role_admin_or_unknown_app_fail(self):
        self.allow()
        for delta in ({'email':'other@example.test'},{'role_ids':[]},{'permissions':['system.admin']}):
            with self.subTest(delta=delta),self.assertRaises(ValueError):
                policy.check(self.work,'practice','read',identity={**self.me,**delta},table='biz_practice')
        with self.assertRaises(ValueError):policy.check(self.work,'unassigned','read',identity=self.me,table='biz_practice')
    def test_unknown_source_and_disallowed_operation_fail(self):
        self.allow();r=self.profile['data_resources']['biz_practice'];r['source']='readable';self.write()
        with self.assertRaises(ValueError):self.check('read')
        r['source']='assigned';r['operations']=['read'];self.write()
        with self.assertRaises(ValueError):self.check('schema')
    def test_shared_table_never_allows_schema_even_if_list_says_yes(self):
        self.allow(True)
        with self.assertRaises(ValueError):self.check('schema')
    def test_shared_reads_require_gate_and_conjunctive_owner_filter(self):
        self.allow(True);filters=[{'field':'owner_student_id','op':'eq','value':USER}]
        self.assertEqual(self.check('read',filters=filters)['operation_check'],'passed')
        for invalid in (None,[],[{'field':'owner_student_id','op':'eq','value':OTHER}],filters+[{'or':[]}],filters+[{'field':'x','op':'or','value':[]} ]):
            with self.subTest(filters=invalid),self.assertRaises(ValueError):self.check('read',filters=invalid)
        self.profile['data_resources']['biz_practice']['gate_verified']=False;self.write()
        with self.assertRaises(ValueError):self.check('read',filters=filters)
    def test_shared_creation_and_updates_cannot_forge_or_transfer_owner(self):
        self.allow(True);row={'id':TABLE,'data':{'owner_student_id':USER}}
        self.assertEqual(self.check('create',data={'owner_student_id':USER})['operation_check'],'passed')
        self.assertEqual(self.check('update',row=row,data={'status':'done'})['operation_check'],'passed')
        for op,args in [('create',{'data':{}}),('create',{'data':{'owner_student_id':OTHER}}),('update',{'row':row,'data':{'owner_student_id':OTHER}}),('delete',{'row':{'id':TABLE,'owner_student_id':OTHER}}),('update',{})]:
            with self.subTest(op=op,args=args),self.assertRaises(ValueError):self.check(op,**args)
    def test_shared_reference_is_limited_to_assigned_app(self):
        self.allow(True)
        with self.assertRaises(ValueError):policy.check(self.work,'site','reference',kind='hosted',identity=self.me,table='biz_practice')
        self.profile['data_resources']['biz_practice']['apps']='practice-site';self.write()
        with self.assertRaises(ValueError):self.check('reference')
    def test_personal_data_can_be_reused_by_assigned_own_hosted_app(self):
        self.allow()
        self.assertEqual(policy.check(self.work,'site','reference',kind='hosted',identity=self.me,table='biz_practice')['operation_check'],'passed')
        resource=self.profile['data_resources']['biz_practice'];resource['origin_app']=resource.pop('app');self.write()
        self.assertEqual(policy.check(self.work,'site','reference',kind='hosted',identity=self.me,table='biz_practice')['operation_check'],'passed')
        self.assertEqual(policy.check(self.work,'site','hosted_access',kind='hosted',identity=self.me)['operation_check'],'passed')
        with self.assertRaises(ValueError):self.check('hosted_access')
    def test_new_table_check_requires_known_app_and_not_existing_target(self):
        self.assertEqual(policy.check(self.work,'practice','create_table',identity=self.me)['operation_check'],'passed')
        with self.assertRaises(ValueError):self.check('create_table')
    def test_created_response_registration_preserves_workspace_and_cannot_overwrite(self):
        receipt={'id':TABLE,'physical_name':'biz_practice','fields':[]}
        secret=self.work/'.aigo/.env';secret.write_bytes(b'PRIVATE_FIXTURE')
        prepare(self.work);(self.work/'notes.txt').write_text('keep')
        original=Path.read_text
        def read(path,*args,**kw):
            if path==secret:raise AssertionError('credentials read')
            return original(path,*args,**kw)
        with mock.patch.object(Path,'read_text',read):
            self.assertTrue(policy.register_created(self.work,'practice',self.me,receipt)['registered'])
            before=(self.work/'.aigo/learning.json').read_bytes()
            self.assertTrue(policy.register_created(self.work,'practice',self.me,receipt)['unchanged'])
            self.assertEqual(before,(self.work/'.aigo/learning.json').read_bytes())
            with self.assertRaises(ValueError):policy.register_created(self.work,'practice',self.me,{**receipt,'id':OTHER})
            upgrade(self.work)
        self.assertEqual(secret.read_bytes(),b'PRIVATE_FIXTURE');self.assertEqual((self.work/'notes.txt').read_text(),'keep')
        self.assertEqual(json.loads((self.work/'.aigo/learning.json').read_text())['data_resources']['biz_practice']['table_id'],TABLE)
    def test_registration_rejects_partial_response_before_writing(self):
        before=(self.work/'.aigo/learning.json').read_bytes()
        with self.assertRaises((ValueError,KeyError)):policy.register_created(self.work,'practice',self.me,{'id':TABLE,'physical_name':'../other'})
        self.assertEqual(before,(self.work/'.aigo/learning.json').read_bytes())
    def test_cli_uses_non_secret_json_and_unknown_operations_stop(self):
        for name in ('.env','token.json','credentials.json'):
            with self.assertRaises(ValueError):policy.read_json(self.work/name)
        with self.assertRaises(ValueError):self.check('unknown')

if __name__=='__main__':unittest.main()
