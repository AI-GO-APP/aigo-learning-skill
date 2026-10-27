"""Create non-secret student workspace files; never log in or overwrite settings."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from uuid import UUID
from learning_scope import tenant_url
from builder_runtime import resolve

SKILL_ROOT = Path(__file__).resolve().parents[1]

COURSE_BLOCK='''<!-- aigo-learning-workspace -->
## AI GO 學習版工作區

本工作區固定為學習版：每個對話都同時使用 aigo-learning 與 aigo-builder，學員不必說「用學習版」。只有學員明確要求改用一般版時才切換。
本工作區同時使用 aigo-learning 與 aigo-builder。Builder 負責技術、資料、串接、開發與部署；學習版負責白話引導、練習與理解驗收。
技術必要資訊與驗證閘門不能省略，提問可分小步。純討論不登入，實作前確認需求與範圍。
每次操作沿用 .aigo/learning.json 的課程帳號、已分配 App 與專屬群組，不借他人帳號。
建立內部 App 時由學員手動選專屬群組，立即回讀；未確認前不匯入、同步、編譯或發布。
使用虛構資料；不把 App 可見度當成資料隔離證明。Hosted 先核對公開內容與最小資料引用，再按 Builder 流程部署及驗收。
平台寫入先過課程範圍檢查，再執行 Builder 適用閘門。保留已有授權，不因切換技能擴大範圍。
功能通過與學員理解分開記錄；代做須標記協助程度。學習版與 Builder 的技術文件不一致時查證實際版本，不另造 API。
<!-- /aigo-learning-workspace -->
'''

def prepare(workspace: Path, *, dry_run=False) -> dict:
    root=workspace.resolve()
    if root.is_relative_to(SKILL_ROOT):raise ValueError('練習工作區必須在技能安裝目錄外')
    updates={}
    for name in ('AGENTS.md','CLAUDE.md'):
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('工作區引導檔路徑異常')
        text=path.read_text(encoding='utf-8') if path.exists() else ''
        addition=COURSE_BLOCK if name=='AGENTS.md' and '<!-- aigo-learning-workspace -->' not in text else ''
        if name=='CLAUDE.md' and '@AGENTS.md' not in text.splitlines():addition='@AGENTS.md\n'
        if addition:updates[path]=text+('\n\n' if text and not text.endswith('\n') else '\n' if text else '')+addition
    if dry_run:return {'workspace':str(root),'guidance_files':[str(p) for p in updates],'platform_operations':0}
    root.mkdir(parents=True,exist_ok=True)
    for path,text in updates.items():path.write_text(text,encoding='utf-8',newline='\n')
    return {'workspace':str(root),'guidance_files':[str(p) for p in updates],'platform_operations':0}


def setup(workspace: Path, tenant: str, email: str, role_id: str) -> dict:
    root = workspace.resolve()
    if root.is_relative_to(SKILL_ROOT):
        raise ValueError('練習工作區必須在技能安裝目錄外')
    base = tenant_url(tenant)
    if not isinstance(email, str) or '@' not in email or '\n' in email or '\r' in email:
        raise ValueError('請使用助教開通的學員 email')
    role = str(UUID(role_id))
    builder=resolve(root)
    config = root/'.aigo'
    outputs = {
        config/'config.json':json.dumps({'base_url':base,'email':email,'apps':{}},ensure_ascii=False,indent=2)+'\n',
        config/'learning.json':json.dumps({'schema':2,'tenant_url':base,'student_email':email,'role_id':role,'apps':{},'hosted_apps':{},'builder_skill_path':builder['root']},ensure_ascii=False,indent=2)+'\n',
        config/'.env':f'AIGO_EMAIL={email}\nAIGO_PASSWORD=\n',
    }
    # Validate every destination before making any change; do not inspect credentials.
    for path in outputs:
        if path.exists() or path.is_symlink():
            raise ValueError('已有設定或憑證，請先核對；不覆蓋既有檔案')
        if not path.resolve().is_relative_to(root):
            raise ValueError('工作區設定路徑異常')
    for name in ('apps','docs','output/pdf','output/source','tmp'):
        path=root/name
        if path.exists() and not path.is_dir():
            raise ValueError('作業資料夾與既有檔案撞名')
        if not path.resolve().is_relative_to(root):
            raise ValueError('工作區資料夾路徑異常')
    ignore=root/'.gitignore'
    if ignore.is_symlink() or not ignore.resolve().is_relative_to(root):
        raise ValueError('版控忽略檔路徑異常')
    current=ignore.read_text(encoding='utf-8') if ignore.exists() else ''
    additions=[line for line in ('.aigo/','.env','.env.*','.venv/','node_modules/','tmp/') if line not in current.splitlines()]
    prepare(root,dry_run=True)
    for name in ('apps','docs','output/pdf','output/source','tmp'): (root/name).mkdir(parents=True,exist_ok=True)
    config.mkdir(parents=True,exist_ok=True)
    for path,content in outputs.items():
        with path.open('x',encoding='utf-8',newline='\n') as stream: stream.write(content)
    if additions:
        with ignore.open('a',encoding='utf-8',newline='\n') as stream:
            stream.write(('\n' if current and not current.endswith('\n') else '')+'\n'.join(additions)+'\n')
    prepare(root)
    return {'workspace':str(root),'created':[str(p) for p in outputs], 'platform_operations':0,
            'next':'請學員在本機編輯器開啟 .aigo/.env，自己填入密碼，完成後再要求核對登入身分。不要讀出該檔內容。'}

def upgrade(workspace: Path) -> dict:
    root=workspace.resolve();builder=resolve(root)
    path=root/'.aigo/learning.json'
    if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('工作區設定路徑異常')
    data=json.loads(path.read_text(encoding='utf-8'))
    tenant_url(data['tenant_url']);UUID(data['role_id'])
    if not isinstance(data.get('student_email'),str) or '@' not in data['student_email']:raise ValueError('學員身分未確認')
    data.update(schema=2,builder_skill_path=builder['root'])
    prepare(root)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return {'workspace':str(root),'upgraded':True,'builder_version':builder['version'],'credentials_accessed':False,'platform_operations':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--tenant-url')
    parser.add_argument('--email')
    parser.add_argument('--role-id')
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--prepare-only',action='store_true')
    group.add_argument('--upgrade-workspace',action='store_true')
    args=parser.parse_args()
    try:
        if args.prepare_only:result=prepare(args.workspace)
        elif args.upgrade_workspace:result=upgrade(args.workspace)
        else:
            if not all((args.tenant_url,args.email,args.role_id)):
                raise ValueError('建立課程設定需助教提供租戶網址、學員 email 與專用群組 id；尚未取得時可先用 --prepare-only')
            result=setup(args.workspace,args.tenant_url,args.email,args.role_id)
    except (ValueError,OSError) as exc:
        print(json.dumps({'setup':'failed','error':str(exc)},ensure_ascii=False)); raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False))
