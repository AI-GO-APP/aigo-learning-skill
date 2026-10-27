"""Course scope adapter. Platform implementation belongs to installed Builder."""
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
from builder_runtime import load_course_scope,resolve

def tenant_url(*args,**kwargs):return load_course_scope().tenant_url(*args,**kwargs)
def check_local(*args,**kwargs):return load_course_scope().check_local(*args,**kwargs)
def check_identity(*args,**kwargs):return load_course_scope().check_identity(*args,**kwargs)
def check_remote(*args,**kwargs):return load_course_scope().check_remote(*args,**kwargs)
def check_hosted_remote(*args,**kwargs):return load_course_scope().check_hosted_remote(*args,**kwargs)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--app',required=True)
    parser.add_argument('--kind',choices=['custom','hosted'],default='custom')
    args=parser.parse_args(argv)
    try:
        root=Path(resolve(args.workspace)['root'])
        command=['uv','run','--project',str(root/'scripts'),'python',str(root/'scripts/aigo_learning_scope.py'),
                 '--workspace',str(args.workspace.resolve()),'--app',args.app,'--kind',args.kind]
        return subprocess.run(command,cwd=args.workspace,check=False).returncode
    except (ValueError,OSError) as exc:
        print(json.dumps({'scope_check':'failed','error':str(exc)},ensure_ascii=False));return 1

if __name__=='__main__':raise SystemExit(main())
