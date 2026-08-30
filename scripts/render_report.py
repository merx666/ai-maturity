# -*- coding: utf-8 -*-
"""段位测评 v3 · 渲染层：固定模板 + AI 范式段位计算 + 揭晓交互。用法: render_report.py scores.json stats.json [out.html]"""
import json,math,sys,os,html as H

def rank_of(total, ach):
    n_ach=sum(1 for v in ach.values() if v)
    tiers=[("聊天框玩家",0),("聊天框玩家 Pro",20),("聊天框玩家 Max",30),
           ("提示词工程师",40),("提示词工程师 Pro",47),("提示词工程师 Max",54),
           ("工具调用者",60),("工具调用者 Pro",65),("工具调用者 Max",70),
           ("智能体指挥",75),("智能体指挥 Pro",80),("智能体指挥 Max",85)]
    alias={"聊天框玩家":"还在和 AI 一问一答","提示词工程师":"会说话了，还没放权",
           "工具调用者":"Function Calling 已觉醒","智能体指挥":"Agentic 时代玩家",
           "多智能体编排者":"同时指挥一个 AI 车间","人机合一":"稀有段位 · 顶点"}
    if total>=95 and n_ach==3: name="人机合一"
    elif total>=90 and n_ach>=2: name="多智能体编排者"
    else:
        name=[t for t,lo in tiers if total>=lo][-1]
        if total>=90: name="智能体指挥 Max"  # 分够但硬成就不够,封顶
    base=name.replace(" Pro","").replace(" Max","")
    # 晋级提示
    if name=="人机合一": nxt="已到顶——保持住"
    elif name=="多智能体编排者":
        nxt=f"距人机合一：{max(0,95-total)} 分" + ("" if n_ach==3 else f"，且需集齐硬成就（缺 {3-n_ach} 枚）")
    else:
        if total>=90: nxt=f"分数已达编排者线，缺硬成就 {3-n_ach} 枚"
        else:
            ups=[(lo,t) for t,lo in tiers if lo>total]
            if ups: nxt=f"距 {ups[0][1]}：{ups[0][0]-total} 分"
            else:
                nxt=f"距多智能体编排者：{90-total} 分" + ("" if n_ach>=2 else f"（另需硬成就≥2，现有 {n_ach} 枚）")
    return name, alias[base], nxt

THEMES={  # 按段位基名取主题：主色/柔和底/特效档
 "冷启动":     {"ac":"#5B8FA8","soft":"#E3EDF2","fx":"none","rarity":"待激活"},
 "聊天框玩家":  {"ac":"#5C6670","soft":"#E8EAEC","fx":"none","rarity":"普通"},
 "提示词工程师":{"ac":"#3E8E5A","soft":"#E2F0E7","fx":"none","rarity":"优秀"},
 "工具调用者":  {"ac":"#2E6FB0","soft":"#E1EBF5","fx":"none","rarity":"稀有"},
 "智能体指挥":  {"ac":"#7C4DBC","soft":"#EDE5F7","fx":"epic","rarity":"史诗"},
 "多智能体编排者":{"ac":"#C8860A","soft":"#F7EDD8","fx":"legend","rarity":"传说"},
 "人机合一":    {"ac":"#B23A2C","soft":"#F3E4E1","fx":"myth","rarity":"神话"},
}
PLAIN={  # 维度白话名 + 一句白话解释（放在卡片最前面）
 "任务交代":("话说清了吗","你安排活儿的时候，它能不能一次听懂"),
 "授权与编排":("敢不敢放手","你是把它当能独立干活的助手，还是当一个要逐步按的按钮"),
 "上下文供给":("材料给够了吗","你有没有把文件和数据给它，还是让它自己猜"),
 "验收与纠偏":("收货严不严","它交活儿之后，你是认真检查，还是照单全收"),
 "资产沉淀":("会不会攒家底","反复做的事，有没有变成一键搞定"),
 "融入度":("用得勤不勤","它是天天上班，还是偶尔客串"),
}
def theme_of(base): return THEMES.get(base,THEMES["聊天框玩家"])
def hex_rgba(h,a):
    h=h.lstrip('#'); return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"

def bars(data,w=560,h=140,color="#B23A2C"):
    if not data: return ''
    mx=max(v for _,v in data) or 1; bw=w/len(data)
    s=f'<svg viewBox="0 0 {w} {h+30}" style="max-width:100%">'
    for i,(k,v) in enumerate(data):
        bh=(h-14)*v/mx
        s+=(f'<rect x="{i*bw+2:.1f}" y="{h-bh:.1f}" width="{bw-4:.1f}" height="{bh:.1f}" fill="{color}" rx="2"/>'
            f'<text x="{i*bw+bw/2:.1f}" y="{h-bh-4:.1f}" text-anchor="middle" font-size="10" fill="#666">{v}</text>'
            f'<text x="{i*bw+bw/2:.1f}" y="{h+12}" text-anchor="middle" font-size="9.5" fill="#666">{H.escape(str(k))}</text>')
    return s+'</svg>'

def radar(dims,ac="#B23A2C"):
    cx,cy,R=150,150,105
    def pol(i,r,n):
        a=math.pi/2-i*2*math.pi/n
        return cx+r*math.cos(a),cy-r*math.sin(a)
    n=len(dims); out=''
    for f in (0.25,0.5,0.75,1.0):
        pts=" ".join(f"{pol(i,R*f,n)[0]:.1f},{pol(i,R*f,n)[1]:.1f}" for i in range(n))
        out+=f'<polygon points="{pts}" fill="none" stroke="#ddd"/>'
    for i in range(n):
        x,y=pol(i,R,n); out+=f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#ddd"/>'
    pts=" ".join(f"{pol(i,R*d['score']/d['max'],n)[0]:.1f},{pol(i,R*d['score']/d['max'],n)[1]:.1f}" for i,d in enumerate(dims))
    out+=f'<polygon points="{pts}" fill="{hex_rgba(ac,.25)}" stroke="{ac}" stroke-width="2"/>'
    for i,d in enumerate(dims):
        x,y=pol(i,R+30,n)
        out+=(f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="middle" font-size="12" fill="#333">{H.escape(PLAIN.get(d["name"],(d["name"],))[0])}</text>'
              f'<text x="{x:.0f}" y="{y+14:.0f}" text-anchor="middle" font-size="11" fill="{ac}" font-weight="bold">{d["score"]}/{d["max"]}</text>')
    return f'<svg viewBox="0 0 300 315" width="340">{out}</svg>'

def main():
    scores=json.load(open(sys.argv[1],encoding='utf-8'))
    stats=json.load(open(sys.argv[2],encoding='utf-8'))
    out=sys.argv[3] if len(sys.argv)>3 else os.path.expanduser('~/Desktop/AI协作成熟度评估报告.html')
    LBL={'claude':'Claude Code','workbuddy':'WorkBuddy','codex':'ChatGPT Work / Codex','qoder':'QoderWork','kimi':'KimiWork','trae':'TRAE Work','domate':'Domate'}
    bc=stats.get('by_client')
    tool=f"全家桶 · {len(bc)} 端" if bc else LBL.get(stats.get('tool'),'AI 助手')
    mild=scores.get('flavor')=='mild'
    if scores.get('rank_mode')=='placement':
        TH=theme_of('冷启动'); _base='冷启动'
    else:
        _n,_a,_x=rank_of(scores['total'],scores.get('achievements',{}))
        _base=_n.replace(' Pro','').replace(' Max','')
        TH=theme_of(_base)
    AC=TH['ac']; SOFT=TH['soft']
    css='''<meta charset="utf-8"><title>AI 协作成熟度评估报告</title><style>
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#F5F6F4;color:#182028;margin:0;padding:24px 16px 80px;line-height:1.7}
.wrap{max-width:860px;margin:0 auto}.center{text-align:center}
.hero{text-align:center;padding:30px 0 6px}
.reveal{display:inline-block;cursor:pointer;position:relative;user-select:none}
.reveal .cover{position:absolute;inset:0;background:linear-gradient(135deg,#182028,#3B4650);color:#fff;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:15px;letter-spacing:2px;transition:opacity .45s,transform .45s;z-index:2}
.reveal.open .cover{opacity:0;transform:scale(1.15);pointer-events:none}
.reveal .inner{padding:8px 30px;border-radius:12px}
.score-big{font-size:84px;font-weight:800;color:#B23A2C;line-height:1.05}
.rank-line{font-size:24px;font-weight:700;margin-top:2px}
.title-pill{display:inline-block;background:#182028;color:#fff;padding:7px 24px;border-radius:999px;font-size:16px}
.sub{color:#6B757E;font-size:13px;margin-top:10px}
.bench{background:#fff;border:1px dashed #DADDD8;border-radius:8px;padding:9px 14px;font-size:12.5px;color:#6B757E;text-align:center;margin:14px auto 0;max-width:640px}
.ach{display:flex;gap:10px;justify-content:center;margin-top:12px;flex-wrap:wrap}
.ach span{font-size:12.5px;padding:4px 12px;border-radius:999px;border:1px solid #DADDD8;background:#fff}
.ach .on{border-color:#2C6B79;color:#2C6B79;font-weight:600}.ach .off{color:#aaa;filter:grayscale(1)}
h2{font-size:19px;border-bottom:2px solid #182028;padding-bottom:7px;margin:42px 0 16px}
.card{background:#fff;border:1px solid #DADDD8;border-radius:8px;padding:15px 20px;margin-bottom:13px}
.ch{display:flex;justify-content:space-between;align-items:baseline;font-size:16.5px}
.sc{color:#B23A2C;font-weight:800;font-size:22px}.sc i{font-style:normal;font-size:12px;color:#999}
.detail{font-size:12.5px;color:#6B757E;border-left:3px solid #E7E9E5;padding-left:10px}
.ev{font-size:12.5px;color:#2C6B79}
.top3 .card{border-left:4px solid #B23A2C}.keep{border-left:4px solid #2C6B79!important}
.tag{font-size:11px;background:#F3E4E1;color:#B23A2C;padding:2px 8px;border-radius:4px;margin-right:8px}
.figc{background:#fff;border:1px solid #DADDD8;border-radius:8px;padding:13px;margin-bottom:13px}
.figc p{font-size:12.5px;color:#6B757E;margin:5px 0 0}
.attr{display:flex;height:32px;border-radius:6px;overflow:hidden;font-size:12.5px;color:#fff;text-align:center;line-height:32px}
.hl{background:#E1EBEC;border-radius:8px;padding:13px 17px;margin-bottom:11px}
.mc{background:#F3E4E1;border-radius:8px;padding:13px 17px}
.private{font-size:11px;color:#B23A2C;margin-bottom:6px}
</style>
<script>function rv(e){e.classList.add('open')}</script>'''
    css=css.replace('#B23A2C',AC).replace('#F3E4E1',SOFT)
    fx=TH['fx']
    if fx=='epic':
        css+=f"<style>.score-big{{text-shadow:0 0 22px {hex_rgba(AC,.35)}}}.title-pill{{box-shadow:0 0 14px {hex_rgba(AC,.3)}}}</style>"
    elif fx=='legend':
        css+=f"<style>.score-big{{text-shadow:0 0 26px {hex_rgba(AC,.55)},0 0 60px {hex_rgba(AC,.25)}}}.hero .reveal .inner{{background:linear-gradient(160deg,{hex_rgba(AC,.10)},transparent 60%)}}.title-pill{{background:linear-gradient(120deg,#8a5c06,{AC});box-shadow:0 0 18px {hex_rgba(AC,.45)}}}</style>"
    elif fx=='myth':
        css+="<style>.score-big,.rank-line{background:linear-gradient(100deg,#B23A2C,#C8860A,#3E8E5A,#2E6FB0,#7C4DBC,#B23A2C);background-size:300% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;animation:holo 6s linear infinite}.title-pill{background:linear-gradient(120deg,#7C4DBC,#B23A2C,#C8860A);background-size:200% 100%;animation:holo 5s linear infinite}@keyframes holo{to{background-position:300% 0}}@media(prefers-reduced-motion:reduce){.score-big,.rank-line,.title-pill{animation:none}}</style>"
    W=[css,'<div class="wrap">']
    scope='全量' if not stats.get('days_filter') else f"近 {stats['days_filter']} 天"
    if scores.get('rank_mode')=='placement':
        p=scores.get('placement') or {'done':stats['human_sessions'],'need':15}
        W.append(f'''<div class="hero">
<div style="font-size:13px;letter-spacing:4px;color:#6B757E;margin-bottom:10px">AI 协作成熟度评估</div>
<div class="score-big" style="font-size:52px">❄️ 冷启动</div>
<div class="rank-line">训练数据 {p["done"]} / {p["need"]} 场</div>
<div class="sub">{tool} · {scope} · 真实任务会话满 {p["need"]} 个即完成冷启动、获得正式段位 · 数据全部本机分析</div>
<div class="bench">冷启动期间不打分——先用起来，段位自然会来。下面是为你准备的起步指南。</div></div>
<h2>你的使用画像</h2><div class="card"><p>{H.escape(scores.get("profile") or "")}</p></div>
<h2>最该先试的三个场景</h2><div class="top3">''')
        for st in (scores.get('starters') or []):
            W.append(f'<div class="card"><b>{H.escape(st.get("name",""))}</b><p>{H.escape(st.get("why",""))}</p><p class="ev">开场可以直接说："{H.escape(st.get("prompt",""))}"</p></div>')
        W.append('</div>')
        if scores.get('potential'):
            W.append(f'<h2>按你的工作，这些能力最可能帮到你</h2><div class="card"><p>{H.escape(scores["potential"])}</p></div>')
    else:
        name,alias,nxt=rank_of(scores['total'],scores.get('achievements',{}))
        ach=scores.get('achievements',{})
        A=lambda k,icon,label: f'<span class="{"on" if ach.get(k) else "off"}">{icon} {label}</span>'
        W.append(f'''<div class="hero">
<div style="font-size:13px;letter-spacing:4px;color:#6B757E;margin-bottom:14px">AI 协作成熟度评估</div>
<div class="reveal" onclick="rv(this)"><div class="cover">👆 点击揭晓分数</div><div class="inner">
  <div class="score-big">{scores["total"]}</div>
  <div class="rank-line">{name} · {alias}</div>\n  <div style="font-size:12px;letter-spacing:3px;color:{AC};margin-top:4px">稀有度 · {TH["rarity"]}</div>
  <div style="color:#6B757E;font-size:13px;margin-top:2px">{H.escape(nxt)}</div></div></div>
<br><div class="reveal" onclick="rv(this)" style="margin-top:14px"><div class="cover">👆 点击揭晓专属称号</div><div class="inner">
  <span class="title-pill">{H.escape(scores.get("title",""))}</span>
  <div class="sub">{H.escape(scores.get("title_reason",""))}</div></div></div>
{f'<div style="max-width:560px;margin:14px auto 0;font-size:14.5px;color:#3B4650">{H.escape(scores.get("summary_plain",""))}</div>' if scores.get("summary_plain") else ""}
<div class="ach">{A("automation","⚙️","无人值守")}{A("parallel","⚡","多线程人生")}{A("consolidation","📦","万物皆可 skill")}</div>
<div class="sub">{tool} · {scope} · 会话 {stats["sessions_all"]}（真人 {stats["human_sessions"]} / 自动化 {stats["automation_sessions"]}）· {H.escape(stats["span"])} · 数据全部本机分析</div>
<div class="bench">📏 本评分体系刻意从严——聊天框/提示词段为新手常态 · 工具调用者已是熟练 · 智能体指挥为重度用户 · 多智能体编排者以上需硬成就，人机合一为稀有段位。</div></div>
<div class="center">{radar(scores["dims"],AC)}</div>''')
        W.append('<h2>对你提升最大的三件事</h2><div class="top3">')
        for t in scores.get('top3',[]):
            W.append(f'<div class="card"><span class="tag">{H.escape(t.get("tag",""))}</span><b>{H.escape(t.get("name",""))}</b><p>现状：{H.escape(t.get("status",""))}</p><p>改法：{H.escape(t.get("action",""))}</p><p class="ev">预期：{H.escape(t.get("expect",""))}</p></div>')
        if scores.get('keep'): W.append(f'<div class="card keep"><b>继续保持</b><p>{H.escape(scores["keep"])}</p></div>')
        W.append('</div><h2>我平时都拿它干什么</h2>')
        tt=stats.get('task_types')
        if tt:
            items=sorted(tt.items(),key=lambda x:-x[1])
            top=items[0]; tot=sum(v for _,v in items) or 1
            W.append(f'<div class="figc"><b>任务类型分布</b>{bars(items,w=640,color=AC)}<p>观察：你最常拿它做「{H.escape(top[0])}」（{top[1]*100//tot}%）。分类由固定规则自动完成，同一份数据每次结果一致。</p></div>')
        if bc:
            cd_=sorted(((v.get('label',k),v.get('human',0)) for k,v in bc.items()),key=lambda x:-x[1])
            xp=stats.get('cross_client_parallel_hours') or 0
            W.append(f'<div class="figc"><b>多端分布（各客户端真人会话）</b>{bars(cd_,w=560,color=AC)}<p>观察：主战场是 {cd_[0][0]}；跨客户端同时段并行 {xp} 个小时——同一小时在两个软件里各干各的，这是"多线程人生"最硬的证据。</p></div>')
        W.append(f'<div class="figc"><b>月度消息量</b>{bars(list(stats["months"].items()),color=AC)}</div>')
        W.append(f'<div class="figc"><b>24 小时活跃分布（北京时间，仅真人会话）</b>{bars([(k,v) for k,v in stats["hours"].items()],w=720,color=AC)}</div>')
        W.append(f'<div class="figc"><b>会话轮次分布</b>{bars(list(stats["turnbins"].items()),w=420,color="#2C6B79")}<p>中位数 {stats["turn_median"]} 轮</p></div>')
        at=scores.get('attribution')
        if at: W.append(f'''<h2>问题归因概览</h2><div class="figc"><div class="attr"><div style="width:{at["user_pct"]}%;background:{AC}">我的原因 {at["user_pct"]}%</div><div style="width:{at["tool_pct"]}%;background:#2C6B79">工具的原因 {at["tool_pct"]}%</div></div><p>我这边：{H.escape(at.get("user_note",""))}｜工具那边：{H.escape(at.get("tool_note",""))}——工具侧问题可反馈给工具方，不全是你的锅。</p></div>''')
        W.append('<h2>六维得分明细</h2>')
        for d in scores['dims']:
            pn,pe=PLAIN.get(d["name"],(d["name"],""))
            W.append(f'<div class="card"><div class="ch"><b>{H.escape(pn)}<span style="font-size:12px;color:#999;font-weight:400;margin-left:8px">{H.escape(d["name"])}</span></b><span class="sc">{d["score"]}<i>/{d["max"]}</i></span></div>'
                     f'<p style="font-size:13px;color:#6B757E;margin:2px 0 8px">这一项看的是：{H.escape(pe)}</p>'
                     f'<p>{H.escape(d.get("comment",""))}</p>'
                     f'<p class="detail">技术明细：{H.escape(d.get("detail",""))}</p>'
                     f'<p class="ev">证据：{H.escape(d.get("evidence",""))}</p></div>')
        tb=scores.get('toolbox')
        if tb: W.append(f'<h2>工具箱体检</h2><div class="card"><p>🔴 同类重叠：{H.escape(tb.get("overlap",""))}</p><p>🟡 闲置：{H.escape(tb.get("idle",""))}</p><p>🟢 该装没装：{H.escape(tb.get("missing",""))}</p></div>')
        hl=scores.get('highlight')
        if hl: W.append(f'<h2>高光时刻</h2><div class="hl">"{H.escape(hl.get("quote",""))}"<br><span style="font-size:13px;color:#2C6B79">{H.escape(hl.get("why",""))}</span></div>')
        sc=scores.get('scene')
        if sc and not mild:
            W.append(f'<h2>名场面</h2><div class="private">🔒 私房内容——分享段位卡时建议只截上半部分</div><div class="reveal" onclick="rv(this)" style="display:block"><div class="cover" style="border-radius:8px">👆 有心理准备再点</div><div class="inner mc" style="padding:13px 17px">"{H.escape(sc.get("quote",""))}"<br><span style="font-size:13px">{H.escape(sc.get("roast",""))}</span></div></div>')
        if scores.get('workshop_focus'):
            W.append(f'<h2 style="border:none">下一步</h2><p>{H.escape(scores["workshop_focus"])}</p>')
    W.append('</div>')
    open(out,'w',encoding='utf-8').write('\n'.join(W))
    print(out)

if __name__=='__main__': main()
