import re,sys,collections
# uso: grp.py <pares> [n]
f=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 30
g={}
c=lambda x:re.sub(r'.*general\[(\d)\].*',r'c\1',x)
nm=lambda x:re.sub(r'\[\d+\]|~DUPLICATE|\d+','#',x.split("|")[-1])[-62:]
for l in open(f):
    if not l.startswith("PATH"): continue
    p=l.rstrip("\n").split("\t")
    if len(p)<7: continue
    clk,slack,dd,fr,to,fc=p[1:7]
    key=(c(fc)+">"+c(clk),nm(fr),nm(to))
    s=float(slack)
    if key not in g or s<g[key][0]: g[key]=(s,float(dd))
for k,v in sorted(g.items(),key=lambda kv:kv[1][0])[:n]: print("%7.3f %6.2f"%v,*k)
