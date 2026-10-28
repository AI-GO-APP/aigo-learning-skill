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
    parser.add_argument('--operation')
    parser.add_argument('--table')
    for name in ('identity','filters','row','data'):parser.add_argument('--'+name+'-file',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.operation:
            from learning_policy import check,read_json,FORBIDDEN
            if args.operation in FORBIDDEN:check(args.workspace,args.app,args.operation)
            check(args.workspace,args.app,args.operation,table=args.table,kind=args.kind,
                  identity=read_json(args.identity_file) if args.identity_file else {},
                  **{k:read_json(getattr(args,k+'_file')) if getattr(args,k+'_file') else None for k in ('filters','row','data')})
        root=Path(resolve(args.workspace)['root'])
        command=['uv','run','--project',str(root/'scripts'),'python',str(root/'scripts/aigo_learning_scope.py'),
                 '--workspace',str(args.workspace.resolve()),'--app',args.app,'--kind',args.kind]
        return subprocess.run(command,cwd=args.workspace,check=False).returncode
    except (ValueError,OSError,KeyError,TypeError) as exc:
        error=str(exc) if isinstance(exc,ValueError) else '設定或非機密核對資料不完整'
        print(json.dumps({'scope_check':'failed','error':error},ensure_ascii=False));return 1

if __name__=='__main__':raise SystemExit(main())
