"""The eleven figures of the transition-failure-matrix article, kept as a worked example.

Run: python3 example_figures.py   (writes SVG + PNG into the current directory)
"""
import os, sys
sys.path.insert(0, os.path.expanduser('~/.claude/skills/publish-to-pathsoflight/scripts'))
from whiteboard import *

# 1 method
f=F(960,330,'先判成败，再看步骤')
f.box(30,130,140,54,'读一条 trace')
f.arrow(172,157,214,157)
f.box(218,122,170,70,['达到用户','目标了吗?'],'y')
f.arrow(390,140,448,98,bend=-8); f.text(410,104,'是',16,GREEN); f.box(452,70,110,50,'通过','g')
f.arrow(390,176,448,216,bend=8); f.text(410,220,'否',16,RED); f.box(452,192,210,54,'只记第一处上游失败','r')
f.arrow(664,219,700,219); f.box(704,192,110,54,['填进','一个格子'],'p',fs=16)
f.arrow(816,219,846,219); f.box(850,180,96,78,['数最大','的格子','先查'],'g',fs=16)
f.line(452,278,662,278); f.text(557,304,'下游的毛病多半是连带的',16,RED)
f.text(898,290,'再做 step',15,GREEN); f.text(898,312,'级诊断',15,GREEN)
f.save('1-method')

# 2 loop
f=F(960,300,'Meridian 的写作–核查循环')
xs=[30,176,322,468,614,804]; names=['聚类','簇判定','写作','取证','核查','标题']
for x,n in zip(xs,names): f.box(x,80,116,52,n,'g' if n in('写作','核查') else 'w')
for i in range(4): f.arrow(xs[i]+118,106,xs[i+1]-4,106)
f.arrow(732,106,800,106); f.text(766,94,'没问题',14,INK)
f.box(614,214,116,52,'改写','p')
f.arrow(640,134,640,210,BLUE,bend=14); f.arrow(704,212,704,136,BLUE,bend=14)
f.text(604,180,'有问题',15,BLUE,'end'); f.text(742,180,'复核',15,BLUE,'start')
f.text(820,232,'LOOP',20,BLUE,'start'); f.text(820,256,'最多两轮',15,BLUE,'start')
f.text(206,196,'流程由代码定',16,GREEN); f.text(206,220,'状态清单从代码抄',16,GREEN)
f.save('2-loop')

# 3 hub
f=F(700,300,'核查 agent：下一步由模型选')
f.box(280,124,140,64,'模型选','y')
for (x,y,t,ax,ay) in [(40,70,'search',278,140),(520,70,'read',422,140),(40,220,'timeline',278,172),(520,220,'verdict',422,172)]:
    f.box(x,y,140,48,t,'p',dotted=True); bx=x+142 if x<350 else x-2
    f.arrow(ax,ay,bx,y+24,both=True,bend=10 if x<350 else -10)
f.text(350,256,'先用哪个、用几次',15,GREEN); f.text(350,278,'都不固定',15,GREEN)
f.save('3-hub')

# 4 trace
f=F(960,240,'跑完之后，trace 还是一串步骤')
f.box(30,92,110,60,'开始')
f.arrow(142,122,182,122); f.box(186,84,200,76,['search ✓','搜到行动代号'],'g',fs=17)
f.arrow(388,122,428,122); f.box(432,84,200,76,['search ✗','换词换偏了'],'r',fs=17)
f.arrow(634,122,674,122); f.box(678,84,200,76,['verdict','连带错, 不记'],'w',dotted=True,fs=17)
f.text(286,190,'↑ 最后做对',17,GREEN); f.text(532,190,'↑ 第一处做错',17,RED)
f.line(186,206,632,206,BLUE); f.text(409,230,'这一格 +1: search → search',16,BLUE)
f.save('4-trace')

# 5 coarsen
f=F(820,380,'工具很多时，先合并')
f.text(120,74,'20 个工具',17,INK); f.text(650,74,'5 个阶段',17,INK)
tools=['web_search','db_query','read_file','open_page','calc','...']; ty=[92+i*42 for i in range(6)]
for t,y in zip(tools,ty): f.box(30,y,180,32,t,'p',dotted=True,fs=15)
st=[('找资料',104),('读资料',188),('计算',272)]
for t,y in st: f.box(560,y,180,48,t,'g')
for i,sy in enumerate([128,128,212,212,296]): f.arrow(214,ty[i]+16,556,sy,bend=(-10 if i%2==0 else 10))
f.line(250,342,570,342); f.text(410,366,'粗矩阵的一格 = 细矩阵那一块的和',16,RED)
f.save('5-coarsen')

# 6 expand
f=F(900,220,'先粗后细')
f.box(30,82,210,58,'填外层粗矩阵')
f.arrow(242,111,300,111); f.box(304,74,260,74,['对角线上数大','= 断在这一步内部'],'y',fs=17)
f.arrow(566,111,624,111); f.box(628,82,230,58,'只展开这一块','g')
f.arrow(742,144,134,144,GREEN,bend=-46); f.text(440,206,'别的块不动，读完再回到外层',16,GREEN)
f.save('6-expand')

# A Hamel
f=F(900,440,'原文的例子：text-to-SQL agent')
ox,oy,dx,dy=matrix(f,20,110,['ParseReq','IntentClass','DecideTool','GenSQL','ExecSQL','PlanCal'],['IntentClass','DecideTool','GenSQL','ExecSQL','PlanCal','ExecCal'],
 {(0,0):('3','y'),(1,1):('4','y'),(2,2):('6','o'),(2,4):('2','y'),(3,3):('12','r',1),(4,4):('5','o'),(5,5):('7','o')},106,40,130,diag=False)
f.arrow(ox+3*dx+50, oy+3*dy+86, ox+3*dx+50, oy+3*dy+44, RED, bend=0); 
f.text(ox+3*dx+50, oy+5*dy+62,'12 条，先查这里',17,RED)
f.save('m1-hamel')

# B loop
f=F(900,400,'三条失败的 trace，各落一格')
ox,oy,dx,dy=matrix(f,20,110,['写作','取证','核查','改写'],['写作','取证','核查','改写'],
 {(1,2):('① 核查误拦好句','r'),(2,3):('② 改写改出新错','r'),(3,2):('③ 复核又误拦','p')},178,48,130)
f.text(ox+2*dx+89, oy+4*dy+34,'↑ 回头的边：落在对角线下方',16,BLUE)
f.text(ox+0.5*dx, oy+4*dy+34,'灰格 = 对角线',14,'#868e96' if False else INK)
f.save('m2-loop')

# C log vs human
f=F(900,270,'同一条 trace，两种看法')
ox,oy,dx,dy=matrix(f,20,96,['系统日志','人对照原文'],['写作','取证','核查','改写'],
 {(0,0):('✓','g'),(0,1):('✓','g'),(0,2):('✓ 发现 1 个问题','g'),(0,3):('✓','g'),
  (1,0):('✓','g'),(1,1):('✓','g'),(1,2):('✗ 判错了','r'),(1,3):('白改一次','y')},170,50,150,diag=False,axes=False)
f.line(ox+2*dx, oy+2*dy+8, ox+3*dx-8, oy+2*dy+8); f.text(ox+2*dx+85, oy+2*dy+34,'没有任何报错，链路照常往下走',16,RED)
f.save('m3-log')

# E agent
f=F(900,400,'这条 trace 落进的格子')
ox,oy,dx,dy=matrix(f,20,110,['开始','search','read','timeline'],['search','read','timeline','verdict'],
 {(1,0):('1','r',1)},160,48,130,diag=False)
f.arrow(ox+dx+40, oy+dy+24, ox+166, oy+dy+24, BLUE)
f.text(ox+dx+48, oy+dy+30,'search 之后又是 search',16,BLUE,'start')
f.text(ox+2*dx, oy+4*dy+34,'同一个工具连用，对角线上也会有数',16,BLUE)
f.save('m4-agent')

# G block
f=F(1040,440,'小 agent 嵌在 workflow 里：分块矩阵')
ox,oy,dx,dy=matrix(f,10,120,['写作','取证','核查','改写'],['写作','取证','核查','改写'],
 {(0,1):('n','w'),(1,2):('n','w'),(2,3):('n','w'),(3,2):('n','w'),(2,2):('展开','p')},84,46,80,diag=False,axes=False)
f.text(ox+2*dx-3,oy-44,'外层：workflow 的步骤',15,GREEN)
ix=560
f.o.append(f'<rect x="{ix-16}" y="60" width="466" height="262" rx="12" fill="{FILL["p"]}" stroke="{INK}" stroke-width="1.5" stroke-dasharray="2 5" stroke-linecap="round"/>')
ox2,oy2,dx2,dy2=matrix(f,ix-6,134,['search','read','timeline'],['search','read','timeline','verdict'],
 {(0,0):('n','w'),(0,1):('n','w'),(0,3):('n','w'),(1,3):('n','w'),(2,3):('n','w')},80,46,90,diag=False,axes=False)
f.text(ix+217,92,'对角块：核查 agent 内部',15,BLUE)
f.arrow(ox+2*dx+88, oy+2*dy+23, ix-20, 200, BLUE, bend=-30)
f.text(520,372,'先填外层；对角线上数大 = 断在这一步内部；只展开这一块',16,GREEN)
f.text(520,404,'非对角块是步骤之间的交接，几乎全空',15,RED)
f.save('m5-block')
