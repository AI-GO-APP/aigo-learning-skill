"""Maintain PDFs with the installed ai-go-app-present AI GO B2B master."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess
from pathlib import Path
from html import escape
ROOT=Path(__file__).resolve().parents[1]

def build(source,output,*,replace=False,present_skill=None,node=None,previews=None):
    from pypdf import PdfReader
    data=json.loads(source.read_text(encoding='utf-8'))
    version=(ROOT/'VERSION').read_text().strip()
    if data['version']!=version: raise ValueError('文件與學習版版本不一致')
    if output.exists() and not replace: raise FileExistsError(output)
    master=Path(present_skill or os.environ.get('AIGO_PRESENT_SKILL',str(ROOT.parent/'FDE ai go app present skill')))
    if not (master/'scripts/deck_kit.py').is_file(): raise ValueError('需指定本機 ai-go-app-present 母版；不能用其他樣式替代')
    spec=importlib.util.spec_from_file_location('present_master',master/'scripts/deck_kit.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    css='''
    .lesson-actions {font-size:23px;line-height:1.65;margin:0;padding-left:27px;}
    .lesson-actions li {margin-bottom:18px;padding-left:6px;}
    .lesson-prompt {font-size:22px;line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere;}
    .lesson-label {color:var(--blue-deep);font-size:20px;font-weight:700;margin:0 0 12px;}
    .lesson-complete {font-size:20px;line-height:1.6;margin-top:16px;padding:14px 18px;background:var(--tint);}
    .lesson-links {font-size:16px;line-height:1.6;margin-top:12px;}
    .lesson-links a {color:var(--blue-deep);margin-right:25px;}
    .lesson-table td,.lesson-table th {font-size:20px;line-height:1.55;padding:12px 16px;}
    .lesson-table {margin:0;}
    .lesson-short {font-size:20px;line-height:1.6;}
    '''
    d=module.Deck(tenant=data.get('audience','課程教材'),app=data.get('app','學習版'),purposes=['操作說明'],
                  title=data['title'],version='v'+version,made=data.get('made','2026-10-27'),extra_css=css)
    d.cover(data.get('subtitle','從第一次對話，到內部系統與對外網站。'),meta=[('對象',data.get('audience','課程學員'))])
    d.slides[-1]['raw']=d.slides[-1]['raw'].replace('<span>租戶</span>','<span>用途</span>').replace('<span>App</span>','<span>文件</span>')
    d.slides[-1]['raw']=d.slides[-1]['raw'].replace('<span>用途</span>'+data.get('audience','課程教材'),'<span>用途</span>操作說明')
    hero='''<div class="shot framed" style="width:690px"><div class="bar"><i></i><i></i><i></i><span>教材路徑示意（非產品畫面）</span></div>
    <div style="padding:46px 38px;color:var(--on-dark);font-size:24px;line-height:1.7;">
    <div style="color:var(--on-dark-2);font-size:18px;">AI GO 學習版</div><h2 style="margin:18px 0 32px;">一個情境，兩個作品</h2>
    <div style="border-left:3px solid var(--blue);padding-left:22px;margin:25px 0;"><b>客人的對外網站</b><br><span style="color:var(--on-dark-2)">瀏覽服務 → 送出申請</span></div>
    <div style="font-size:30px;color:var(--blue);margin:12px 0;">↓</div>
    <div style="border-left:3px solid var(--blue);padding-left:22px;margin:25px 0;"><b>自己的內部系統</b><br><span style="color:var(--on-dark-2)">收到申請 → 確認與跟進</span></div>
    <div style="font-size:18px;color:var(--on-dark-2);margin-top:32px;">先確認、再實作；成果與理解分開驗收。</div></div></div>'''
    d.slides[-1]['raw']=d.slides[-1]['raw'].replace('<div class="cv-r"></div>','<div class="cv-r">'+hero+'</div>')
    d.toc(howto=False)
    previous=None
    for page in data['pages']:
        if page['part']!=previous:
            label,_,title=page['part'].partition(' ')
            d.divider(page['part'],'PART '+label,title or label,'依順序前進，完成一個小成果再進下一步。')
            previous=page['part']
        if not page.get('prompt') or not page.get('success'): raise ValueError('每個情景需提示詞與完成條件')
        if page.get('table'):
            rows=page['table']; body=d.table(rows[0],rows[1:],cls='compact lesson-table')
            body+='<div class="lesson-short"><b>範例提示詞：</b>'+escape(page['prompt']).replace('\n','<br>')+'</div>'
        else:
            actions='<ol class="lesson-actions">'+''.join('<li>'+escape(row)+'</li>' for row in page['steps'])+'</ol>'
            prompt='<div class="lesson-label">可直接貼給 AI</div><div class="lesson-prompt">'+escape(page['prompt'])+'</div>'
            body=d.row(d.col(actions,650),d.col(prompt,700))
        body+='<div class="lesson-complete"><b>完成後應看到：</b>'+escape(page['success'])+'</div>'
        if page.get('links'):
            body+='<div class="lesson-links">'+''.join('<a href="'+escape(url,quote=True)+'">'+escape(label)+' ↗</a>' for label,url in page['links'])+'</div>'
        d.slide(page['part'],page['title'],page['intro'],body,kicker='AI GO · '+page['part'])
    d.back_cover('從一個小成果開始',data.get('closing','先確認、再實作；做得到，也說得清楚。'),contact=['課程問題請洽助教'])
    output.parent.mkdir(parents=True,exist_ok=True); html=source.with_suffix('.html'); d.write(html)
    text=re.sub(r'<link[^>]+(?:fonts.googleapis.com|fonts.gstatic.com)[^>]*>','',html.read_text(encoding='utf-8'))
    html.write_text(text,encoding='utf-8',newline='\n')
    cmd=[str(node or shutil.which('node') or 'node'),str(master/'scripts/render.mjs'),'--html',str(html),'--pdf',str(output)]
    if previews: cmd+=['--png',str(previews)]
    subprocess.run(cmd,check=True)
    count=len(PdfReader(output).pages)
    if count!=len(d._layout()) or output.stat().st_size>20*1024*1024: raise ValueError('頁數或檔案大小不符')
    data['rendered_pages']=count; source.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return {'pages':count,'version':version,'master':'ai-go-app-present / AI GO B2B 1600x900',
            'master_version':(master/'VERSION').read_text().strip(),
            'master_css_sha256':hashlib.sha256((master/'scripts/deck.css').read_bytes()).hexdigest(),'visual_review':'pending'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'docs/handbook.json'); p.add_argument('--output',type=Path,default=ROOT/'assets/student-handbook.pdf')
    p.add_argument('--present-skill',type=Path); p.add_argument('--node',type=Path); p.add_argument('--previews',type=Path); p.add_argument('--replace',action='store_true')
    a=p.parse_args(); print(json.dumps(build(a.source,a.output,replace=a.replace,present_skill=a.present_skill,node=a.node,previews=a.previews),ensure_ascii=False))
