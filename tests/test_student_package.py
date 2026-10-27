import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tools')]
import check_update as integrity
import student_update as updater
import build_release as release


def fixture(version='0.1.0', body='old'):
    files = {'SKILL.md':body.encode(), 'VERSION':version.encode(), 'scripts/check_update.py':b'# checker',
             'scripts/student_update.py':b'# updater', 'references/student-rules.md':body.encode()}
    meta = {'schema':1,'skill':'aigo-learning','version':version,'builder_version':'1.72.0',
            'files':{name:hashlib.sha256(value).hexdigest() for name,value in files.items()}}
    files['PACKAGE.json'] = json.dumps(meta).encode()
    return files, meta


def write(root, files):
    for name, value in files.items():
        path = root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(value)


def zipped(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out,'w') as archive:
        for name,value in files.items():
            archive.writestr('repo-commit/'+name,value)
    return out.getvalue()


class UpdateTests(unittest.TestCase):
    def test_first_check_applies_new_runtime_and_preserves_workspace(self):
        old,_ = fixture()
        new,_ = fixture('0.2.0','new rules')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'skill'; root.mkdir()
            work = Path(temp)/'work/.aigo'; work.mkdir(parents=True)
            (work/'config.json').write_text('student setting')
            write(root,old)
            with mock.patch.object(updater,'fetch',side_effect=[json.dumps({'sha':'a'*40}).encode(),zipped(new)]) as fetch:
                result = updater.update(root,now=50000,state_file=Path(temp)/'state.json')
            self.assertTrue(result['updated'])
            self.assertEqual(integrity.validate(root)['version'],'0.2.0')
            self.assertEqual((work/'config.json').read_text(),'student setting')
            self.assertEqual(fetch.call_count,2)

    def test_three_hour_throttle_and_same_commit_after_interval(self):
        files,_ = fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'skill'; root.mkdir(); write(root,files)
            state=Path(temp)/'state.json'
            state.write_text(json.dumps({'last_check':50000,'installed_commit':'a'*40}))
            with mock.patch.object(updater,'fetch') as fetch:
                result=updater.update(root,now=50001,state_file=state)
            self.assertEqual(result['status'],'throttled'); fetch.assert_not_called()
            with mock.patch.object(updater,'fetch',return_value=json.dumps({'sha':'a'*40}).encode()) as fetch:
                result=updater.update(root,now=60800,state_file=state)
            self.assertEqual(result['status'],'current'); self.assertEqual(fetch.call_count,1)

    def test_commit_change_without_version_bump_still_updates(self):
        old,_=fixture(); new,_=fixture(body='corrected same version')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'skill'; root.mkdir(); write(root,old)
            state=Path(temp)/'state.json'; state.write_text(json.dumps({'last_check':0,'installed_commit':'b'*40}))
            with mock.patch.object(updater,'fetch',side_effect=[json.dumps({'sha':'a'*40}).encode(),zipped(new)]):
                result=updater.update(root,now=50000,state_file=state)
            self.assertTrue(result['updated']); self.assertEqual((root/'SKILL.md').read_text(),'corrected same version')

    def test_corrupt_download_does_not_modify_install(self):
        old,_=fixture(); bad,_=fixture('0.2.0'); bad['SKILL.md']=b'tampered'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'skill'; root.mkdir(); write(root,old)
            with mock.patch.object(updater,'fetch',side_effect=[json.dumps({'sha':'a'*40}).encode(),zipped(bad)]):
                with self.assertRaises(ValueError):
                    updater.update(root,now=50000,state_file=Path(temp)/'state.json')
            self.assertEqual((root/'SKILL.md').read_bytes(),old['SKILL.md'])
            integrity.validate(root)

    def test_offline_check_is_throttled_and_keeps_old_files(self):
        old,_=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'skill'; root.mkdir(); write(root,old); state=Path(temp)/'state.json'
            with mock.patch.object(updater,'fetch',side_effect=TimeoutError):
                with self.assertRaises(TimeoutError): updater.update(root,now=50000,state_file=state)
            with mock.patch.object(updater,'fetch') as fetch:
                result=updater.update(root,now=50001,state_file=state)
            self.assertEqual(result['status'],'throttled'); fetch.assert_not_called(); integrity.validate(root)

    def test_workspace_or_credentials_inside_install_prevents_update(self):
        for name in ('.aigo','.env'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temp:
                root=Path(temp); write(root,fixture()[0])
                (root/name).mkdir() if name=='.aigo' else (root/name).write_text('fake credential')
                with mock.patch.object(updater,'fetch') as fetch:
                    with self.assertRaisesRegex(ValueError,'憑證'): updater.update(root)
                fetch.assert_not_called()

    def test_development_copy_skips_network(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(updater,'development_copy',return_value=True),mock.patch.object(updater,'fetch') as fetch:
            result=updater.update(Path(temp)); self.assertEqual(result['status'],'development-copy'); fetch.assert_not_called()

    def test_unsafe_or_non_runtime_paths_are_refused(self):
        for name in ('../outside','/outside','scripts/../../outside','.aigo/config.json','C:/secret','tools/private.py','scripts\\escape.py'):
            with self.subTest(name=name),self.assertRaises(ValueError): updater.safe_name(name)

    def test_apply_failure_restores_previous_install(self):
        old,_=fixture(); new,meta=fixture('0.2.0','new')
        with tempfile.TemporaryDirectory() as temp:
            root,stage=Path(temp)/'root',Path(temp)/'stage'; root.mkdir(); stage.mkdir(); write(root,old); write(stage,new)
            actual=updater.atomic_write; attempts=[0]
            def fail_once(path,value):
                attempts[0]+=1
                if attempts[0]==2: raise OSError('simulated write failure')
                actual(path,value)
            with mock.patch.object(updater,'atomic_write',side_effect=fail_once):
                with self.assertRaises(OSError): updater.apply_staged(root,stage,meta)
            for name,value in old.items(): self.assertEqual((root/name).read_bytes(),value)
            integrity.validate(root)

    def test_unknown_local_files_are_not_deleted_on_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root,stage=Path(temp)/'root',Path(temp)/'stage'; root.mkdir(); stage.mkdir()
            old,_=fixture(); new,meta=fixture('0.2.0'); write(root,old); write(stage,new)
            (root/'notes.txt').write_text('my notes')
            with self.assertRaises(ValueError): updater.apply_staged(root,stage,meta)
            self.assertEqual((root/'notes.txt').read_text(),'my notes')
            self.assertEqual((root/'SKILL.md').read_bytes(),old['SKILL.md'])

    def test_repair_local_tamper_even_when_commit_matches(self):
        old,_=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'skill'; root.mkdir(); write(root,old); (root/'SKILL.md').write_text('corrupted')
            state=Path(temp)/'state.json'; state.write_text(json.dumps({'last_check':0,'installed_commit':'a'*40}))
            with mock.patch.object(updater,'fetch',side_effect=[json.dumps({'sha':'a'*40}).encode(),zipped(old)]):
                result=updater.update(root,now=50000,state_file=state)
            self.assertTrue(result['updated']); integrity.validate(root)

    def test_colliding_directory_or_parent_file_is_refused_before_mutation(self):
        for collision, child in [('scripts/collision.py',False), ('scripts/helpers',True)]:
            with self.subTest(collision=collision),tempfile.TemporaryDirectory() as temp:
                root,stage=Path(temp)/'root',Path(temp)/'stage'; root.mkdir(); stage.mkdir()
                old,_=fixture(); new,meta=fixture('0.2.0','new')
                name=collision+'/readme.txt' if child else collision
                new[name]=b'new'; meta['files'][name]=hashlib.sha256(b'new').hexdigest()
                new['PACKAGE.json']=json.dumps(meta).encode()
                write(root,old); write(stage,new)
                if child: (root/collision).write_bytes(b'personal file')
                else: (root/collision).mkdir()
                with self.assertRaisesRegex(ValueError,'撞名'): updater.apply_staged(root,stage,meta)
                for name,value in old.items(): self.assertEqual((root/name).read_bytes(),value)

    def test_manifest_directory_to_file_transition_keeps_every_old_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            root,stage=Path(temp)/'root',Path(temp)/'stage'; root.mkdir(); stage.mkdir()
            old,old_meta=fixture(); old['scripts/helpers/readme.txt']=b'old'
            old_meta['files']['scripts/helpers/readme.txt']=hashlib.sha256(b'old').hexdigest()
            old['PACKAGE.json']=json.dumps(old_meta).encode()
            new,meta=fixture('0.2.0','new'); new['scripts/helpers']=b'new'
            meta['files']['scripts/helpers']=hashlib.sha256(b'new').hexdigest()
            new['PACKAGE.json']=json.dumps(meta).encode(); write(root,old); write(stage,new)
            with self.assertRaisesRegex(ValueError,'撞名'): updater.apply_staged(root,stage,meta)
            for name,value in old.items(): self.assertEqual((root/name).read_bytes(),value)
            integrity.validate(root)

    def test_missing_or_corrupted_manifest_is_repaired_without_deleting_unknown_files(self):
        for damaged in (None,b'not json',b'[]'):
            with self.subTest(damaged=damaged),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'root'; root.mkdir(); files,_=fixture(); write(root,files)
                if damaged is None: (root/'PACKAGE.json').unlink()
                else: (root/'PACKAGE.json').write_bytes(damaged)
                with mock.patch.object(updater,'fetch',side_effect=[json.dumps({'sha':'a'*40}).encode(),zipped(files)]):
                    result=updater.update(root,now=50000,state_file=Path(temp)/'state.json')
                self.assertTrue(result['updated']); integrity.validate(root)

    def test_malformed_throttle_timestamp_does_not_block_future_checks(self):
        for stamp in ('yesterday',None,True,[],float('nan'),float('inf'),10**1000):
            with self.subTest(stamp=stamp),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'root'; root.mkdir(); files,_=fixture(); write(root,files)
                state=Path(temp)/'state.json'; state.write_text(json.dumps({'last_check':stamp}))
                with mock.patch.object(updater,'fetch',side_effect=[json.dumps({'sha':'a'*40}).encode(),zipped(files)]):
                    result=updater.update(root,now=50000,state_file=state)
                self.assertEqual(result['status'],'current')

    def test_version_mismatch_and_oversized_archive_rejected_before_install(self):
        files,meta=fixture(); files['VERSION']=b'999'
        meta['files']['VERSION']=hashlib.sha256(b'999').hexdigest()
        files['PACKAGE.json']=json.dumps(meta).encode()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'版本不一致'):
                updater.stage_archive(zipped(files),Path(temp))
        with tempfile.TemporaryDirectory() as temp,mock.patch.object(updater,'MAX_ARCHIVE',1):
            with self.assertRaisesRegex(ValueError,'大小限制'):
                updater.stage_archive(zipped(fixture()[0]),Path(temp))
            self.assertFalse(list(Path(temp).iterdir()))


class ContentAndReleaseTests(unittest.TestCase):
    def test_all_pages_have_prompt_and_order_is_from_setup_to_acceptance(self):
        book=json.loads((ROOT/'docs/handbook.json').read_text(encoding='utf-8'))
        self.assertEqual(book['version'],(ROOT/'VERSION').read_text().strip())
        self.assertTrue(all(p['prompt'].strip() and p['success'].strip() for p in book['pages']))
        parts=[p['part'] for p in book['pages']]
        self.assertLess(parts.index('A 課前準備'),parts.index('C 對外網站'))
        self.assertGreater(parts.index('F 常見問題'),parts.index('D 驗收與交付'))
        self.assertEqual(len([p for p in parts if p=='E 六階段課綱']),3)
        self.assertGreater(book['rendered_pages'],len(book['pages']))

    def test_rules_and_terminology_present(self):
        rules=(ROOT/'references/student-rules.md').read_text(encoding='utf-8')
        for number in range(1,26): self.assertIn(f'R{number:02d} ',rules)
        for path in [ROOT/'SKILL.md',*(ROOT/'references').glob('*.md'),ROOT/'docs/handbook.json']:
            text=path.read_text(encoding='utf-8'); self.assertNotIn('內勤',text,path.name); self.assertNotIn('窗口',text,path.name)
            for obsolete in ('普通模式','一般模式','學習模式','學生版','投資 Agent'): self.assertNotIn(obsolete,text,path.name)
        self.assertIn('建立後立即',rules); self.assertIn('不編譯或發布',rules)

    def test_builder_is_installed_dependency_and_platform_tools_are_not_copied(self):
        upstream=json.loads((ROOT/'UPSTREAM.json').read_text(encoding='utf-8'))
        self.assertEqual(upstream['policy'],'installed-skill-dependency')
        self.assertEqual(upstream['minimum_version'],'1.74.0')
        files=release.runtime_files()
        self.assertFalse(any(name.startswith('technical/') for name in files))
        self.assertNotIn('scripts/aigo_auth.py',files)
        self.assertNotIn('scripts/aigo_publish.py',files)
        self.assertIn('scripts/builder_runtime.py',files)

    def test_runtime_does_not_export_builder_admin_or_maintenance(self):
        files=release.runtime_files()
        self.assertNotIn('references/member-admin.md',files)
        self.assertNotIn('scripts/report_issue.py',files)
        self.assertNotIn('tools/vendor_builder.py',files)
        self.assertIn('assets/student-handbook.pdf',files)
        self.assertEqual(json.loads((ROOT/'PACKAGE.json').read_text(encoding='utf-8'))['files'],{n:release.sha(v) for n,v in sorted(files.items())})

    def test_deterministic_release_and_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b=Path(temp)/'a',Path(temp)/'b'
            one,two=release.build(a),release.build(b)
            self.assertEqual(one['sha256'],two['sha256'])
            self.assertTrue(all(name.isascii() for name in one['sha256']))
            with self.assertRaises(FileExistsError): release.build(a)


if __name__=='__main__': unittest.main()
