"""Create non-secret student workspace files; never log in or overwrite settings."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from uuid import UUID
from learning_scope import tenant_url

SKILL_ROOT = Path(__file__).resolve().parents[1]


def setup(workspace: Path, tenant: str, email: str, role_id: str) -> dict:
    root = workspace.resolve()
    if root.is_relative_to(SKILL_ROOT):
        raise ValueError('練習工作區必須在技能安裝目錄外')
    base = tenant_url(tenant)
    if not isinstance(email, str) or '@' not in email or '\n' in email or '\r' in email:
        raise ValueError('請使用助教開通的學員 email')
    role = str(UUID(role_id))
    config = root/'.aigo'
    outputs = {
        config/'config.json':json.dumps({'base_url':base,'email':email,'apps':{}},ensure_ascii=False,indent=2)+'\n',
        config/'learning.json':json.dumps({'tenant_url':base,'student_email':email,'role_id':role,'apps':{},'hosted_apps':{}},ensure_ascii=False,indent=2)+'\n',
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
    for name in ('apps','docs','output/pdf','output/source','tmp'): (root/name).mkdir(parents=True,exist_ok=True)
    config.mkdir(parents=True,exist_ok=True)
    for path,content in outputs.items():
        with path.open('x',encoding='utf-8',newline='\n') as stream: stream.write(content)
    if additions:
        with ignore.open('a',encoding='utf-8',newline='\n') as stream:
            stream.write(('\n' if current and not current.endswith('\n') else '')+'\n'.join(additions)+'\n')
    return {'workspace':str(root),'created':[str(p) for p in outputs], 'platform_operations':0,
            'next':'請學員在本機編輯器開啟 .aigo/.env，自己填入密碼，完成後再要求核對登入身分。不要讀出該檔內容。'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--tenant-url',required=True)
    parser.add_argument('--email',required=True)
    parser.add_argument('--role-id',required=True)
    args=parser.parse_args()
    try: result=setup(args.workspace,args.tenant_url,args.email,args.role_id)
    except (ValueError,OSError) as exc:
        print(json.dumps({'setup':'failed','error':str(exc)},ensure_ascii=False)); raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False))
