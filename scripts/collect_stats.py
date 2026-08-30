# -*- coding: utf-8 -*-
"""段位测评 v3 · 统计层：确定性统计，模型不许自己算数。
支持 Claude Code (~/.claude/projects) 与 WorkBuddy (~/.workbuddy/projects)。"""
import json,glob,os,sys,datetime,collections,statistics,argparse,re

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--tool',default='auto')
    p.add_argument('--list',action='store_true',help='仅探测本机客户端并退出')
    p.add_argument('--probe-deep',action='store_true',help='深度扫描可疑数据目录')
    p.add_argument('--days',type=int,default=0,help='0=全量')
    p.add_argument('--out',default='.')
    return p.parse_args()

# ─── 客户端注册表（跨 OS）────────────────────────────────────────────
# 每条候选路径带 os（mac/win/any）与 verified（True=本机实测过格式；False=文档/推断候选，待验证）
# 路径里的 ~ 在 Windows 展开为 %USERPROFILE%；$APPDATA/$LOCALAPPDATA 用环境变量展开
CLIENTS={
 'claude':{'label':'Claude Code','parser':'claude','paths':[
    {'os':'any','dir':'~/.claude/projects','glob':'*/*.jsonl','verified':True}]},
 'workbuddy':{'label':'WorkBuddy','parser':'workbuddy','paths':[
    {'os':'any','dir':'~/.workbuddy/projects','glob':'*/*.jsonl','verified':True},
    {'os':'win','dir':'$APPDATA/WorkBuddy/projects','glob':'*/*.jsonl','verified':False}]},
 'codex':{'label':'ChatGPT Work / Codex','parser':'generic','paths':[
    {'os':'any','dir':'~/.codex/sessions','glob':'**/*.jsonl','verified':True},
    {'os':'win','dir':'$APPDATA/ChatGPT/sessions','glob':'**/*.jsonl','verified':False}]},
 'trae':{'label':'TRAE Work','parser':'generic','paths':[
    {'os':'any','dir':'~/.trae','glob':'**/*.jsonl','verified':False},
    {'os':'mac','dir':'~/Library/Application Support/Trae','glob':'**/*.jsonl','verified':False},
    {'os':'win','dir':'$APPDATA/Trae','glob':'**/*.jsonl','verified':False}]},
 'qoder':{'label':'QoderWork','parser':'generic','paths':[
    {'os':'any','dir':'~/.qoderwork','glob':'**/*.jsonl','verified':False},
    {'os':'any','dir':'~/.qoder-cli','glob':'**/*.jsonl','verified':False},
    {'os':'any','dir':'~/.qoder','glob':'**/*.jsonl','verified':False},
    {'os':'win','dir':'$APPDATA/Qoder','glob':'**/*.jsonl','verified':False}]},
 'kimi':{'label':'KimiWork','parser':'generic','paths':[
    {'os':'any','dir':'~/.kimi','glob':'**/*.jsonl','verified':False},
    {'os':'mac','dir':'~/Library/Application Support/kimi-desktop','glob':'**/*.jsonl','verified':False},
    {'os':'win','dir':'$APPDATA/Kimi','glob':'**/*.jsonl','verified':False}]},
 'doubao':{'label':'豆包工作 / DoubaoWork','parser':'generic','paths':[
    {'os':'mac','dir':'~/Library/Application Support/DoubaoWork','glob':'**/*.jsonl','verified':False},
    {'os':'any','dir':'~/.doubao','glob':'**/*.jsonl','verified':False},
    {'os':'win','dir':'$APPDATA/DoubaoWork','glob':'**/*.jsonl','verified':False}]},
 'krowork':{'label':'KroWork','parser':'generic','paths':[
    {'os':'mac','dir':'~/Library/Application Support/krow-app','glob':'**/*.jsonl','verified':False},
    {'os':'any','dir':'~/.krowork','glob':'**/*.jsonl','verified':False},
    {'os':'win','dir':'$APPDATA/krow-app','glob':'**/*.jsonl','verified':False}]},
 'openclaw':{'label':'OpenClaw','parser':'generic','paths':[
    {'os':'any','dir':'~/.openclaw/agents','glob':'*/sessions/*.jsonl','verified':False}]},
 'gemini':{'label':'Gemini / Antigravity','parser':'generic','paths':[
    {'os':'any','dir':'~/.gemini/antigravity/brain','glob':'*/.system_generated/logs/*.jsonl','verified':False},
    {'os':'any','dir':'~/.gemini','glob':'**/*.jsonl','verified':False}]},
 'hermes':{'label':'Hermes Agent','parser':'generic','paths':[
    {'os':'any','dir':'~/.hermes','glob':'**/*.jsonl','verified':False}]},
 'domate':{'label':'Domate','parser':'generic','paths':[
    {'os':'any','dir':'~/.domate','glob':'**/*.jsonl','verified':False},
    {'os':'mac','dir':'~/Library/Application Support/Domate','glob':'**/*.jsonl','verified':False},
    {'os':'win','dir':'$APPDATA/Domate','glob':'**/*.jsonl','verified':False}]},
}
import platform
CUR_OS='win' if platform.system()=='Windows' else 'mac'
def _expand(p):
    p=p.replace('$APPDATA',os.environ.get('APPDATA','~/AppData/Roaming'))
    p=p.replace('$LOCALAPPDATA',os.environ.get('LOCALAPPDATA','~/AppData/Local'))
    return os.path.expanduser(p)
def probe():
    """返回 {client: {label, files, base, glob, parser, verified}}，每客户端取命中文件最多的候选路径"""
    found={}
    for k,c in CLIENTS.items():
        best=None
        for cand in c['paths']:
            if cand['os'] not in ('any',CUR_OS): continue
            base=_expand(cand['dir'])
            if not os.path.isdir(base): continue
            n=len(glob.glob(os.path.join(base,cand['glob']),recursive=True))
            if n and (best is None or n>best['files']):
                best={'label':c['label'],'files':n,'base':base,'glob':cand['glob'],
                      'parser':c['parser'],'verified':cand['verified']}
        if best: found[k]=best
    return found
def probe_deep():
    """深度探针：在常见根目录下扫任何含会话文件的可疑目录（未注册客户端的兜底）"""
    roots=[os.path.expanduser('~')]
    if CUR_OS=='mac': roots.append(os.path.expanduser('~/Library/Application Support'))
    else:
        roots+= [os.environ.get('APPDATA',''),os.environ.get('LOCALAPPDATA','')]
    hits=[]
    names=re.compile(r'workbuddy|trae|qoder|domate|chatgpt|codex|claude|copilot|kimi|krow|doubao|豆包|openclaw|hermes|gemini|qwen|iflow|minimax|moonshot|cursor|dsh',re.I)
    for root in filter(os.path.isdir,roots):
        try: entries=os.listdir(root)
        except OSError: continue
        for e in entries:
            if not names.search(e): continue
            p=os.path.join(root,e)
            if not os.path.isdir(p): continue
            n=len(glob.glob(os.path.join(p,'**','*.jsonl'),recursive=True))
            m=len(glob.glob(os.path.join(p,'**','*.db'),recursive=True))
            if n or m: hits.append({'dir':p,'jsonl':n,'db':m})
    return hits
def detect_tool(pref):
    found=probe()
    if not found:
        deep=probe_deep()
        msg='ERROR: 注册路径下未发现会话数据。'
        if deep: msg+=' 深度探针发现以下可疑目录（把该输出发给管理员以补充适配）: '+json.dumps(deep,ensure_ascii=False)
        sys.exit(msg)
    if pref!='auto':
        if pref not in found: sys.exit(f'ERROR: 未找到 {pref} 的数据。本机发现: '+', '.join(found))
        f=found[pref]; return pref,f
    best=max(found,key=lambda k:found[k]['files'])
    return best,found[best]

def iter_msgs(fp, tool):
    """yield (kind, role, text, ts)  kind: msg|side"""
    try: fh=open(fp,encoding='utf-8',errors='replace')
    except OSError: return
    with fh:
        for line in fh:
            try: d=json.loads(line)
            except ValueError: continue
            if CLIENTS.get(tool,{}).get('parser')=='claude':
                t=d.get('type')
                if t not in ('user','assistant'): continue
                if d.get('isSidechain'): yield 'side',t,'',d.get('timestamp'); continue
                m=d.get('message',{}); c=m.get('content')
                if isinstance(c,list):
                    c=' '.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type')=='text')
                yield 'msg',t,(c or ''),d.get('timestamp')
            elif tool not in CLIENTS or CLIENTS[tool].get('parser')=='generic':
                # 启发式：找 role/content 常见变体（实验性支持）
                if isinstance(d.get('payload'),dict): d={**d.get('payload'),'timestamp':d.get('timestamp')}
                msg=d.get('message') if isinstance(d.get('message'),dict) else {}
                role=d.get('role') or msg.get('role') or d.get('type')
                if role not in ('user','assistant'): continue
                c=d.get('content') or msg.get('content') or d.get('text')
                if isinstance(c,list):
                    c=' '.join((x.get('text') or x.get('content') or '') for x in c if isinstance(x,dict))
                yield 'msg',role,str(c or ''),d.get('timestamp') or d.get('ts') or d.get('created_at')
            else:  # workbuddy: type=message, content 为 [{type:input_text/output_text, text}], ts 为毫秒
                if d.get('type')!='message': continue
                c=d.get('content')
                if isinstance(c,list):
                    c=' '.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type') in ('input_text','output_text'))
                c=str(c or '')
                m=re.search(r'<user_query>(.*?)</user_query>',c,re.S)
                if m: c=m.group(1)
                elif '<system-reminder' in c: c=re.sub(r'<system-reminder.*?</system-reminder>','',c,flags=re.S)
                yield 'msg',d.get('role',''),c,d.get('timestamp')

def pt(ts):
    if not ts: return None
    if isinstance(ts,(int,float)) or (isinstance(ts,str) and ts.isdigit()):
        v=float(ts)
        if v>1e12: v/=1000  # 毫秒
        try: return datetime.datetime.fromtimestamp(v,datetime.timezone.utc)
        except (ValueError,OSError): return None
    try: return datetime.datetime.fromisoformat(str(ts).replace('Z','+00:00'))
    except ValueError: return None

SKIP=('<command-','<local-command','Caveat:','<system-reminder')
# 任务类型分类（顺序即优先级，首中即停）
TASK_RULES=[
 ('文件处理',   r'整理|清理|文件夹|重命名|转换格式|压缩|磁盘|归档|太乱|能删|删掉|备份'),
 ('网页操作',   r'网页|爬|抓取|浏览器|去.{0,6}(网站|页面).{0,6}(操作|填|点)'),
 ('自动化配置', r'定时|自动(跑|运行|执行|生成|推送)|做成\s*(skill|技能|命令)|固化|挂(个|一个)?任务|安装|装一下|装上|接入|配置.{0,6}(mcp|MCP|工具|数据源)|建.{0,3}(skill|命令)'),
 ('编程开发',   r'代码|bug|debug|部署|脚本|报错|重构|前端|后端|开发|编译|git|修一下|项目|继续做|接着做|小程序|网站'),
 ('数据分析',   r'数据|统计|报表|行情|财务|估值|excel|Excel|xlsx|表格|算一下|对账|核对|涨|跌'),
 ('文本撰写',   r'写|翻译|文案|纪要|报告|ppt|PPT|文档|邮件|润色|起草|讲稿|摘要|简历|logo|Logo|wiki|知识库|转成文章|设计(一个|个|下)'),
 ('生活助手',   r'旅|行程|露营|攻略|假期|买|推荐一下|餐厅|周末去|好吃|好玩'),
 ('信息检索',   r'查|搜|调研|研究|了解|找找|找一下|介绍|资料|有没有|哪些'),
 ('咨询问答',   r'为什么|怎么看|是什么|怎么办|建议|评价|你觉得|怎么理解|讨论|测评|评测|review|reveiw|评审|审一下|打分'),
]
def classify_task(text):
    for name,pat in TASK_RULES:
        if re.search(pat,text): return name
    return '其它' 
NEG=re.compile(r'不对|错了|不是这|重新|你怎么|又失败|别这|不行|改一下|没有啊|翻车|太臭|太差|难看|不满意|wrong|not right|redo')

def collect_client(tool,info,days):
    files=glob.glob(os.path.join(info['base'],info['glob']),recursive=True)
    sessions={}
    for f in files:
        proj=os.path.basename(os.path.dirname(f))
        if 'observer' in proj: continue
        for kind,role,text,ts in iter_msgs(f,tool):
            se=sessions.setdefault(f,{'proj':proj,'client':tool,'u':[],'a':0,'side':0})
            if kind=='side': se['side']+=1; continue
            if role=='assistant': se['a']+=1; continue
            if role!='user': continue
            text=text.strip()
            if not text or any(text.startswith(x) for x in SKIP): continue
            if re.match(r'^<[a-zA-Z_][a-zA-Z_-]*[ >]', text): continue
            t=pt(ts)
            se['u'].append({'ts':t.isoformat() if t else '','txt':text[:500]})
    sess=[x for x in sessions.values() if x['u']]
    if days:
        latest=max((pt(m['ts']) for x in sess for m in x['u'] if pt(m['ts'])),default=None)
        if latest:
            cut=latest-datetime.timedelta(days=days)
            sess=[x for x in sess if any(pt(m['ts']) and pt(m['ts'])>=cut for m in x['u'])]
    return sess,len(files)

def deposits_of(tool):
    if tool=='claude':
        return {'skills':len(glob.glob(os.path.expanduser('~/.claude/skills/*'))),
                'commands':len(glob.glob(os.path.expanduser('~/.claude/commands/*'))),
                'cmd_label':'自定义命令','memo':os.path.exists(os.path.expanduser('~/CLAUDE.md'))}
    if tool=='workbuddy':
        n=len(glob.glob(os.path.expanduser('~/.workbuddy/skills/*')))+len(glob.glob(os.path.expanduser('~/.workbuddy/plugins/*')))
        try:
            import sqlite3
            c=sqlite3.connect(os.path.expanduser('~/.workbuddy/workbuddy.db')).execute('select count(*) from automations').fetchone()[0]
        except Exception: c=0
        return {'skills':n,'commands':c,'cmd_label':'自动化任务','memo':os.path.exists(os.path.expanduser('~/.workbuddy/IDENTITY.md'))}
    return {'skills':0,'commands':0,'cmd_label':'沉淀','memo':False}

def main():
    a=parse_args()
    if a.list:
        print(json.dumps({'os':CUR_OS,'clients':{k:{'label':v['label'],'files':v['files'],'verified':v['verified']} for k,v in probe().items()}},ensure_ascii=False)); return
    if a.probe_deep:
        print(json.dumps(probe_deep(),ensure_ascii=False)); return
    os.makedirs(a.out,exist_ok=True)
    if a.tool=='all':
        found=probe()
        if not found: sys.exit('ERROR: 未发现任何客户端数据')
        sess=[]; nfiles=0; by_client={}; dep={'skills':0,'commands':0,'cmd_label':'沉淀(多端合计)','memo':False}
        unverified=[k for k,v in found.items() if not v['verified']]
        for k,v in found.items():
            cs,nf=collect_client(k,v,a.days)
            sess+=cs; nfiles+=nf
            d=deposits_of(k)
            dep['skills']+=d['skills']; dep['commands']+=d['commands']; dep['memo']=dep['memo'] or d['memo']
            by_client[k]={'label':v['label'],'files':nf,'sessions':len(cs)}
        tool='all'; info={'verified':len(unverified)==0}
    else:
        tool,info=detect_tool(a.tool)
        sess,nfiles=collect_client(tool,info,a.days)
        dep=deposits_of(tool); by_client=None
    # ── 自动化分离（合并后统一做）──
    pref=collections.Counter(x['u'][0]['txt'][:60] for x in sess)
    auto_pref={p for p,c in pref.items() if c>=3}
    sched=re.compile(r'<scheduled-task|session-scoped Stop hook|cron|定时任务调度')
    auto=[x for x in sess if x['u'][0]['txt'][:60] in auto_pref or sched.search(x['u'][0]['txt'])]
    human=[x for x in sess if x not in auto]
    if by_client:
        for k in by_client:
            by_client[k]['human']=sum(1 for x in human if x['client']==k)
            by_client[k]['automation']=sum(1 for x in auto if x['client']==k)
    allts=sorted(t for x in human for m in x['u'] if (t:=pt(m['ts'])))
    days_set=set(t.date() for t in allts)
    months=collections.Counter(t.strftime('%Y-%m') for t in allts)
    hours=collections.Counter((t.hour+8)%24 for t in allts)
    turns=[len(x['u']) for x in human]
    tb={'1-2':0,'3-5':0,'6-10':0,'10+':0}
    for n in turns: tb['1-2' if n<=2 else '3-5' if n<=5 else '6-10' if n<=10 else '10+']+=1
    bucket=collections.defaultdict(set); xbucket=collections.defaultdict(set)
    for x in human:
        for m in x['u']:
            t=pt(m['ts'])
            if t:
                bucket[t.strftime('%Y-%m-%d %H')].add(id(x))
                xbucket[t.strftime('%Y-%m-%d %H')].add(x.get('client') or 'one')
    par=sum(1 for v in bucket.values() if len(v)>=2)
    xpar=sum(1 for v in xbucket.values() if len(v)>=2)  # 跨客户端同时段
    def key(t): return re.sub(r'[\s\d，。,.!？?]','',t[:30])
    ttypes=collections.Counter(classify_task(x['u'][0]['txt']) for x in human)
    rep=collections.Counter(key(x['u'][0]['txt']) for x in human)
    repeats=[[k,c] for k,c in rep.most_common(10) if c>=3 and k]
    first,last=(allts[0].date(),allts[-1].date()) if allts else (None,None)
    span=(last-first).days+1 if first else 0
    r30=sum(1 for t in allts if (allts[-1]-t).days<=30) if allts else 0
    p30=sum(1 for t in allts if 30<(allts[-1]-t).days<=60) if allts else 0
    stats={'tool':tool,'os':CUR_OS,'path_verified':info['verified'],'files':nfiles,
      'sessions_all':len(sess),'automation_sessions':len(auto),'human_sessions':len(human),
      'by_client':by_client,'cross_client_parallel_hours':xpar if by_client else None,
      'span':f'{first} ~ {last}','span_days':span,'active_days':len(days_set),
      'active_ratio':round(len(days_set)/span,2) if span else 0,
      'months':dict(sorted(months.items())),'hours':{str(k):hours.get(k,0) for k in range(24)},
      'turn_median':statistics.median(turns) if turns else 0,'turnbins':tb,
      'par_ratio':round(par/len(bucket),2) if bucket else 0,'sidechain_msgs':0,
      'task_types':dict(ttypes.most_common()),'deposits':dep,'repeats':repeats,'msgs30':r30,'msgs_prev30':p30,
      'trend':'升' if r30>p30*1.2 else ('降' if r30<p30*0.8 else '平'),
      'days_filter':a.days}
    json.dump(stats,open(os.path.join(a.out,'stats.json'),'w'),ensure_ascii=False,indent=1)
    tag=(lambda x: f"[{x['client']}]") if by_client else (lambda x:'')
    with open(os.path.join(a.out,'first_messages.txt'),'w',encoding='utf-8') as f:
        for i,x in enumerate(sorted(human,key=lambda z:z['u'][0]['ts'] or '')):
            f.write(f"[{i+1}|{(x['u'][0]['ts'] or '')[:10]}|{len(x['u'])}轮]{tag(x)} {x['u'][0]['txt'][:200]}\n")
    with open(os.path.join(a.out,'feedback.txt'),'w',encoding='utf-8') as f:
        for x in human:
            for m in x['u'][1:]:
                if NEG.search(m['txt']): f.write(f"[{(m['ts'] or '')[:10]}]{tag(x)} {m['txt'][:150]}\n")
    with open(os.path.join(a.out,'closings.txt'),'w',encoding='utf-8') as f:
        for x in human:
            if len(x['u'])>=2: f.write(f"[{len(x['u'])}轮]{tag(x)} {x['u'][-1]['txt'][:120]}\n")
    print(json.dumps({'tool':tool,'os':CUR_OS,'path_verified':info['verified'],
        'files':nfiles,'sessions':len(sess),'automation':len(auto),'human':len(human),
        'by_client':by_client,'cross_client_parallel_hours':xpar if by_client else None,
        'span':stats['span'],'human_lt15_placement_mode':len(human)<15,'out':a.out},ensure_ascii=False))

if __name__=='__main__': main()
