"""Local course operation checks. No platform requests or permission changes."""
from __future__ import annotations
import argparse,json,os,re,tempfile
from pathlib import Path
from uuid import UUID
from builder_runtime import load_course_scope

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN={'roles','members','data_policy','internal_group','clear_table'}
DATA_OPERATIONS={'read','create','update','delete','schema','reference'}

def read_json(path):
    path=Path(path)
    if path.name.startswith('.env') or path.name in ('token.json','credentials.json'):raise ValueError('只使用非機密核對資料')
    return json.loads(path.read_text(encoding='utf-8'))

def context(workspace,app,identity,kind='custom'):
    root=Path(workspace).resolve()
    profile=read_json(root/'.aigo/learning.json');config=read_json(root/'.aigo/config.json')
    scope=load_course_scope(root)
    target=scope.check_local(profile,config,profile['tenant_url'],app,kind)
    scope.check_identity(target,identity)
    user_id=str(UUID(identity['id']))
    if 'system.admin' in identity.get('permissions',[]):raise ValueError('請使用本人學員身分')
    if not isinstance(identity.get('role_ids'),list) or profile['role_id'] not in identity['role_ids']:raise ValueError('專屬群組與本人身分未核對')
    return profile,target,user_id

def check(workspace,app,operation,*,identity=None,table=None,kind='custom',filters=None,row=None,data=None):
    if operation in FORBIDDEN:raise ValueError('此操作不在學生學習版可操作範圍；保留設定並由助教核對')
    if operation not in DATA_OPERATIONS|{'create_table','hosted_access'}:raise ValueError('操作種類未核對')
    profile,target,user_id=context(workspace,app,identity or {},kind)
    result={'operation_check':'passed','platform_operations':0,'server_authorization_verified':False}
    if operation=='hosted_access':
        if kind!='hosted':raise ValueError('公開設定僅供已核定的本人對外網站')
        return result
    if operation=='create_table':
        if table is not None:raise ValueError('建立新表不可指定既有表為操作目標')
        return {**result,'next':'依已確認規格建立新表；取得成功回應後登記，再讀寫或引用'}
    resources=profile.get('data_resources',{})
    resource=resources.get(table) if isinstance(resources,dict) else None
    if not isinstance(resource,dict):raise ValueError('資料表未列入本題核定範圍；不依名稱或可讀取推定歸屬')
    UUID(resource['table_id'])
    known_apps=set(profile.get('apps',{}))|set(profile.get('hosted_apps',{}))
    if resource.get('source') not in ('created','assigned'):raise ValueError('資料表來源未核對')
    allowed=resource.get('operations',[])
    if not isinstance(allowed,list) or operation not in allowed:raise ValueError('本題未核定此資料操作')
    mode=resource.get('mode')
    if mode=='personal':
        if resource.get('origin_app',resource.get('app')) not in known_apps:raise ValueError('資料表建立來源未核對')
        if resource.get('owner_user_id')!=user_id:raise ValueError('資料表歸屬與本人不符')
    elif mode=='shared':
        if resource.get('source')!='assigned':raise ValueError('共用資料尚未核定')
        apps=resource.get('apps',[resource.get('app')])
        if not isinstance(apps,list) or app not in apps:raise ValueError('共用資料未核定供此作品使用')
        if operation=='schema':raise ValueError('不可更動共用表結構')
        field=resource.get('owner_field')
        if not isinstance(field,str) or not re.fullmatch(r'[a-z][a-z0-9_]*',field):raise ValueError('共用資料歸屬欄位未核對')
        if resource.get('gate_verified') is not True:raise ValueError('共用資料授權尚未核對')
        if operation=='read':
            if not isinstance(filters,list) or not all(isinstance(f,dict) for f in filters):raise ValueError('共用資料查詢需明確限定本人')
            if any(set(f)-{'field','op','value'} or f.get('op') in ('or','not','and') for f in filters):raise ValueError('共用資料查詢條件格式未核對')
            if not any(f.get('field')==field and f.get('op')=='eq' and f.get('value')==user_id for f in filters):
                raise ValueError('共用資料查詢未限定本人')
        if operation in ('update','delete'):
            values=row.get('data',row) if isinstance(row,dict) else {}
            if not isinstance(values,dict) or values.get(field)!=user_id:raise ValueError('資料列歸屬尚未讀回核對')
            UUID(row['id'])
        if operation=='create' and (not isinstance(data,dict) or data.get(field)!=user_id):raise ValueError('新增資料必須歸屬本人')
        if isinstance(data,dict) and field in data and data[field]!=user_id:raise ValueError('不可變更資料歸屬')
    else:raise ValueError('資料表用途未核對')
    return {**result,'table':table,'mode':mode}

def register_created(workspace,app,identity,receipt,kind='custom'):
    """Record a successful create-table response; never approve an existing unknown table."""
    root=Path(workspace).resolve();path=root/'.aigo/learning.json'
    if root.is_relative_to(ROOT) or path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('工作區設定路徑異常')
    profile,_,user_id=context(root,app,identity,kind)
    table_id=str(UUID(receipt['id']));name=receipt['physical_name']
    if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_]*',name) or not isinstance(receipt.get('fields'),list):
        raise ValueError('新表建立回應不完整')
    resources=profile.setdefault('data_resources',{})
    if not isinstance(resources,dict):raise ValueError('資料範圍設定格式異常')
    entry={'table_id':table_id,'origin_app':app,'mode':'personal','source':'created','owner_user_id':user_id,
           'operations':sorted(DATA_OPERATIONS)}
    if name in resources:
        if resources[name]!=entry:raise ValueError('已有資料範圍設定，不能用建立回應覆寫')
        return {'registered':False,'unchanged':True,'platform_operations':0}
    resources[name]=entry
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',dir=path.parent,delete=False) as stream:
        temporary=Path(stream.name);json.dump(profile,stream,ensure_ascii=False,indent=2);stream.write('\n')
    try:os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
    return {'registered':True,'table':name,'platform_operations':0}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--app',required=True)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--operation');group.add_argument('--register-created-table',type=Path)
    p.add_argument('--identity-file',type=Path);p.add_argument('--table');p.add_argument('--kind',choices=['custom','hosted'],default='custom')
    for name in ('filters','row','data'):p.add_argument('--'+name+'-file',type=Path)
    a=p.parse_args(argv)
    try:
        # Forbidden operations stop before any file/dependency/credential access.
        if a.operation in FORBIDDEN:check(a.workspace,a.app,a.operation)
        identity=read_json(a.identity_file) if a.identity_file else {}
        if a.register_created_table:result=register_created(a.workspace,a.app,identity,read_json(a.register_created_table),a.kind)
        else:
            result=check(a.workspace,a.app,a.operation,identity=identity,table=a.table,kind=a.kind,
                         **{k:read_json(getattr(a,k+'_file')) if getattr(a,k+'_file') else None for k in ('filters','row','data')})
    except (ValueError,OSError,KeyError,TypeError) as exc:
        message=str(exc) if isinstance(exc,ValueError) else '設定或非機密核對資料不完整'
        print(json.dumps({'operation_check':'stopped','error':message,'platform_operations':0},ensure_ascii=False));return 1
    print(json.dumps(result,ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
