"""Resolve the installed Builder dependency. Never vendor or overwrite its tools."""
from __future__ import annotations
import argparse,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MINIMUM=(1,74,0)

def metadata(path: Path,strict=True):
    root=path.expanduser().resolve()
    if root.name=='SKILL.md':root=root.parent
    text=(root/'SKILL.md').read_text(encoding='utf-8')
    if not re.search(r'^name:\s*aigo-builder\s*$',text,re.M):raise ValueError('指定位置不是 aigo-builder')
    version=(root/'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Builder 版本格式未確認')
    parts=tuple(map(int,version.split('.')))
    compatible=MINIMUM<=parts<(2,0,0) and (root/'scripts/aigo_learning_scope.py').is_file()
    if strict and not compatible:raise ValueError('本學習版需要 Builder 1.74.0 以上、2.0.0 以下；請先檢查更新，未完成前只做討論與本機規劃')
    return {'root':str(root),'version':version,'compatible':compatible,'minimum':'1.74.0','platform_operations':0}

def resolve(workspace=None,explicit=None,strict=True):
    work=Path(workspace or Path.cwd()).resolve()
    chosen=explicit or os.environ.get('AIGO_BUILDER_SKILL')
    if chosen:return metadata(Path(chosen),strict)
    profile=work/'.aigo/learning.json'
    if profile.is_file():
        value=json.loads(profile.read_text(encoding='utf-8')).get('builder_skill_path')
        if value:return metadata(Path(value),strict)
    candidates=[work/'.agents/skills/aigo-builder',work/'.claude/skills/aigo-builder',
                ROOT.parent/'aigo-builder',Path.home()/'.agents/skills/aigo-builder',
                Path.home()/'.claude/skills/aigo-builder',Path.home()/'.codex/skills/aigo-builder']
    for root in candidates:
        if (root/'SKILL.md').is_file():return metadata(root,strict)
    raise ValueError('尚未找到 Builder。請依 README 安裝 aigo-builder＋aigo-learning，或提供已核對的 Builder 安裝路徑；不要用舊技術副本代替')

def load_course_scope(workspace=None):
    root=Path(resolve(workspace)['root'])
    spec=importlib.util.spec_from_file_location('_aigo_builder_course_scope',root/'scripts/aigo_learning_scope.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=Path.cwd())
    parser.add_argument('--builder',type=Path)
    parser.add_argument('--update',action='store_true')
    args=parser.parse_args(argv)
    try:
        info=resolve(args.workspace,args.builder,strict=False)
        if args.update:subprocess.run([sys.executable,str(Path(info['root'])/'scripts/check_update.py')],check=True)
        result=resolve(args.workspace,args.builder)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print(json.dumps({'builder':'not-ready','error':str(exc),'platform_operations':0},ensure_ascii=False));return 1

if __name__=='__main__':raise SystemExit(main())
