import re,sys,collections
f=sys.argv[1]
rows=[]
for l in open(f):
    if not l.startswith("LV\t"): continue
    p=l.rstrip("\n").split("\t")
    if len(p)<8: continue
    d,lv,sl,dd,fr,to,fc=p[1:8]
    try: rows.append((d,int(lv),float(sl),float(dd),fr,to))
    except: pass
def ab(x):
    x=x.replace("core:CORE|","").replace("\\gen_csr:","").replace("\\gen_zihpm:","")
    x=re.sub(r'_OTERM\d+|_NEW\d*|~DUPLICATE|_RESYN\d+|_NEW_REG\d+','',x)
    x=re.sub(r'\[\d+\]','[#]',x); x=re.sub(r'gen_index:\d+:','',x); x=re.sub(r'\b\w+:(\w+)','\\1',x)
    x=re.sub(r'(?<=[a-z_])\d+\b','#',x)
    parts=x.split("|")
    return ("/".join(parts[-3:]))[-70:]
def mod(x):
    x=x.replace("core:CORE|","")
    for k,n in [("hpm_counter_bank","Zihpm banco"),("csr_file","csr_file"),("reg_id_ex","ID/EX"),("reg_ex_mem","EX/MEM"),("reg_mem_wb","MEM/WB"),("reg_if_id","IF/ID"),("pc_fetch","PC"),("stage_if","IF"),("stage_ex","EX"),("stage_mem","MEM"),("misaligned","desalinhado"),("DCACHE","dcache"),("ICACHE","icache"),("dcache","dcache"),("icache","icache"),("multdiv","muldiv"),("SDRAM","sdram"),("sdram","sdram"),("reg_file","banco de registradores"),("hazard","HDU")]:
        if k in x: return n
    return x.split("|")[0][:20]
print("DOMINIOS", {d:len([r for r in rows if r[0]==d]) for d in set(r[0] for r in rows)})
for d in ["c3","c2","sdram","dram_clk"]:
    rs=sorted([r for r in rows if r[0]==d],key=lambda r:(-r[1],r[2]))
    print("\n## top por niveis:",d,"n=",len(rs))
    seen=collections.OrderedDict()
    for r in rs:
        k=(mod(r[4]),mod(r[5]),ab(r[4]),ab(r[5]))
        if k not in seen: seen[k]=[r,1]
        else: seen[k][1]+=1
    for k,(r,c) in list(seen.items())[:50]:
        print("%2d niv %6.2f ns folga %7.3f x%-4d %s -> %s"%(r[1],r[3],r[2],c,k[2],k[3]))
print("\n## agregado por modulo de destino (c3 e c2): >6, >8, >10, max, e max de atraso")
agg=collections.defaultdict(list)
for r in rows:
    if r[0] in("c3","c2"): agg[(r[0],mod(r[5]))].append(r)
for (d,m),rs in sorted(agg.items(),key=lambda kv:-max(r[1] for r in kv[1])):
    print("%-3s %-24s n=%-5d >=6:%-5d >=8:%-5d >=10:%-4d max=%-2d maxatraso=%.2f"%(d,m,len(rs),sum(r[1]>=6 for r in rs),sum(r[1]>=8 for r in rs),sum(r[1]>=10 for r in rs),max(r[1] for r in rs),max(r[3] for r in rs)))
print("\n## niveis altos com atraso baixo (roteamento bom) e niveis baixos com atraso alto (roteamento ruim), c3")
c3=[r for r in rows if r[0]=="c3"]
hi=sorted([r for r in c3 if r[1]>=9],key=lambda r:r[3])[:8]
for r in hi: print("%2d niv %6.2f ns folga %7.3f %s -> %s"%(r[1],r[3],r[2],ab(r[4]),ab(r[5])))
print("--")
lo=sorted([r for r in c3 if r[1]<=6],key=lambda r:-r[3])[:8]
for r in lo: print("%2d niv %6.2f ns folga %7.3f %s -> %s"%(r[1],r[3],r[2],ab(r[4]),ab(r[5])))
import statistics
byl=collections.defaultdict(list)
for r in c3: byl[r[1]].append(r[3])
print("\natraso medio por nivel (c3):",{k:round(statistics.mean(v),2) for k,v in sorted(byl.items())})
