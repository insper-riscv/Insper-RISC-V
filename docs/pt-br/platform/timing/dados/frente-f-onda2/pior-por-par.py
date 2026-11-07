import sys,re,collections
f=sys.argv[1]
best=collections.defaultdict(lambda:(99,0))
for l in open(f):
    if not l.startswith("PATH"): continue
    p=l.rstrip("\n").split("\t")
    if len(p)<7: continue
    c=lambda x:re.sub(r'.*general\[(\d)\].*',r'c\1',x)
    k=c(p[6])+">"+c(p[1]); s=float(p[2])
    if s<best[k][0]: best[k]=(s,float(p[3]))
print(" ".join("%s %.3f(%.1fns)"%(k,v[0],v[1]) for k,v in sorted(best.items())))
