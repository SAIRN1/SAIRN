import re,sys
sys.path.insert(0,sys.argv[1])  # usage: strip_cross.py <dir containing projection_order_scan.py> <file.js>
import projection_order_scan as P
f=sys.argv[2]
src=open(f,encoding='utf-8').read()
m=P.mask(src)
lines=src.split('\n')
# strip lists with line numbers
strips=[]
for mt in re.finditer(r'storedBlob\s*\(',m):
    o=mt.end()-1;c=P.match(m,o,'(',')')
    args=P.split_top(m,o+1,c)
    if len(args)>=2:
        lst=src[args[1][0]:args[1][1]]
        keys=set(re.findall(r"'([\w]+)'",lst))
        strips.append((src.count('\n',0,mt.start())+1,keys))
rows=[]
for mt in re.finditer(r'Object\.assign\s*\(',m):
    o=mt.end()-1;c=P.match(m,o,'(',')')
    args=P.split_top(m,o+1,c)
    if len(args)<2: continue
    t=[m[a:b] for a,b in args]
    if not P.is_keyed_literal(t[0]): continue
    later=[src[a:b].strip() for (a,b),x in zip(args[1:],t[1:]) if not P.is_literal(x)]
    if not later: continue
    lit=src[args[0][0]:args[0][1]]
    lm=m[args[0][0]:args[0][1]]
    # top-level keys of first literal
    inner_a=args[0][0]+lm.index('{')+1
    inner_b=args[0][0]+lm.rindex('}')
    keys=[]
    for a,b in P.split_top(m,inner_a,inner_b):
        km=re.match(r'\s*[\'"]?([A-Za-z_$][\w$]*)[\'"]?\s*(:|$|,)',src[a:b])
        if km: keys.append(km.group(1))
    ln=src.count('\n',0,mt.start())+1
    near=[(l,k) for l,k in strips if abs(l-ln)<=260]
    union=set().union(*[k for _,k in near]) if near else set()
    missing=[k for k in keys if k not in union]
    rows.append((ln,keys,later[0][:30],missing,len(near)))
for ln,keys,later,missing,nn in rows:
    flag='' if not missing else '  <== NOT IN ANY NEARBY STRIP LIST: %s'%missing
    if 'headers' in later or later in ('extra','base','patch','result','// The'): continue
    print('%d %s <- %s (strips nearby:%d)%s'%(ln,keys,later,nn,flag))
