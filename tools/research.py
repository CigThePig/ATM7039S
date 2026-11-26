#!/usr/bin/env python3
"""Offline evidence tools. Never opens devices, mounts images, or executes inputs."""
import argparse
import ast
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
CONFIDENCE = ['verified', 'strongly-supported', 'inferred', 'speculative', 'unknown']

def save(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def number(expr, names=None):
    """Evaluate integer C subset; no eval, calls, attributes, or preprocessor execution."""
    if len(expr)>1024: raise ValueError('integer expression too long')
    expr = re.sub(r'\b(0[xX][0-9a-fA-F]+|[0-9]+)[uUlL]+\b', r'\1', expr)
    tree = ast.parse(expr, mode='eval')
    names = names or {}
    def visit(n):
        if isinstance(n, ast.Expression): return visit(n.body)
        if isinstance(n, ast.Constant) and type(n.value) is int: return n.value
        if isinstance(n, ast.Name) and n.id in names: return names[n.id]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.Invert, ast.USub, ast.UAdd)):
            v = visit(n.operand)
            return ~v if isinstance(n.op, ast.Invert) else -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            a = [visit(x) for x in n.args]
            if n.func.id == 'BIT' and len(a) == 1 and 0 <= a[0] < 64: return 1 << a[0]
            if n.func.id == 'GENMASK' and len(a) == 2 and 0 <= a[1] <= a[0] < 64:
                return ((1 << (a[0] - a[1] + 1)) - 1) << a[1]
        if isinstance(n, ast.BinOp):
            a, b = visit(n.left), visit(n.right)
            if isinstance(n.op, (ast.LShift, ast.RShift)) and not 0 <= b < 64: raise ValueError('shift out of bounds')
            ops = {ast.Add: lambda: a+b, ast.Sub: lambda: a-b, ast.BitOr: lambda: a|b,
                   ast.BitAnd: lambda: a&b, ast.LShift: lambda: a<<b, ast.RShift: lambda: a>>b,
                   ast.Mult: lambda: a*b}
            if type(n.op) in ops: return ops[type(n.op)]()
        raise ValueError('unsupported integer expression')
    return visit(tree)

def constants(text, source):
    rows, names, pending = [], {}, []
    for line, value in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*#define\s+([A-Za-z_]\w*)(\s+)(.+)', value)
        if m:
            expression = re.split(r'/\*|//', m[3])[0].strip()
            pending.append((m[1], expression, line))
    while pending:
        rest = []
        for name, expression, line in pending:
            try: value = number(expression, names)
            except (ValueError, SyntaxError, KeyError, TypeError): rest.append((name, expression, line)); continue
            names[name] = value
            rows.append(dict(name=name, expression=expression, value=value, source=source, line=line))
        if len(rest) == len(pending): break
        pending = rest
    return dict(definitions=sorted(rows, key=lambda x:x['line']), unresolved=[dict(name=n,expression=e,line=l) for n,e,l in pending])

def dts(text):
    """Parse flattened numeric DTS only. Unsupported macros/includes fail explicitly."""
    text = text.lstrip('\ufeff')
    token_re = re.compile(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*|[{};=<>\[\],:]|[^\s{};=<>\[\],:]+', re.S)
    tokens = [(m.group(), text.count('\n',0,m.start())+1) for m in token_re.finditer(text) if not m.group().startswith(('/*','//'))]
    i, stack, nodes = 0, [], []
    while i < len(tokens):
        t, line = tokens[i]
        if t == '/dts-v1/':
            if tokens[i+1][0] != ';': raise ValueError('bad DTS version')
            i += 2; continue
        if t == '}':
            if not stack: raise ValueError('unbalanced DTS')
            stack.pop(); i += 1
            if i < len(tokens) and tokens[i][0] == ';': i += 1
            continue
        if t in ('/include/', '/plugin/', '/delete-node/') or t.startswith('&'): raise ValueError('use a flattened DTS; includes/overlays unsupported')
        # labels are optional, but phandle references remain unsupported
        if i+1 < len(tokens) and tokens[i+1][0] == ':': i += 2; t,line=tokens[i]
        j=i+1
        # commas are legal inside property names, unlike value list separators
        while j+1 < len(tokens) and tokens[j][0] == ',': t+=','+tokens[j+1][0]; j+=2
        if j >= len(tokens): raise ValueError('truncated DTS')
        op=tokens[j][0]
        if op == '{':
            path='/' if t=='/' else (stack[-1]['path'].rstrip('/')+'/'+t if stack else t)
            node=dict(path=path, line=line, properties={}); nodes.append(node); stack.append(node); i=j+1; continue
        if not stack: raise ValueError('property outside node')
        if op==';': value=True; i=j+1
        elif op=='=':
            j+=1; raw=[]
            while j<len(tokens) and tokens[j][0]!=';': raw.append(tokens[j][0]); j+=1
            if j==len(tokens): raise ValueError('unterminated property')
            if raw and all(x.startswith('"') or x==',' for x in raw):
                value=[]
                for x in raw:
                    if x!=',': value.extend(ast.literal_eval(x).split('\0'))
            elif raw and raw[0]=='<':
                if raw[-1]!='>' or raw.count('<')!=raw.count('>'): raise ValueError('unbalanced DTS cells')
                value=[]
                for x in raw:
                    if x not in ('<','>',','):
                        if not re.fullmatch(r'0[xX][0-9a-fA-F]+|[0-9]+',x): raise ValueError('non-numeric DTS cell: '+x)
                        v=int(x,16) if x.lower().startswith('0x') else int(x,10)
                        if not 0<=v<=0xffffffff: raise ValueError('DTS cell out of range')
                        value.append(v)
            elif raw and raw[0]=='[' and raw[-1]==']': value={'bytes': ''.join(raw[1:-1])}
            else: raise ValueError('unsupported DTS value: '+str(raw))
            i=j+1
        else: raise ValueError('unsupported DTS syntax near '+t)
        if t in stack[-1]['properties']: raise ValueError('duplicate property '+t)
        stack[-1]['properties'][t]=value
    if stack: raise ValueError('unclosed DTS node')
    return nodes

def fdt(data):
    if len(data)<40: raise ValueError('short FDT header')
    magic,total,offstruct,offstrings,offreserve,version,last,boot,size_strings,size_struct=struct.unpack_from('>10I',data)
    if magic!=0xd00dfeed or version<17 or last>17: raise ValueError('unsupported FDT header')
    if not 40<=total<=len(data): raise ValueError('invalid FDT total size')
    for off,size in [(offstruct,size_struct),(offstrings,size_strings)]:
        if off<40 or off+size>total: raise ValueError('FDT block outside image')
    strings=data[offstrings:offstrings+size_strings]
    reserved=[]; r=offreserve
    while True:
        if r<40 or r+16>total: raise ValueError('invalid reservation map')
        a,s=struct.unpack_from('>QQ',data,r); r+=16
        if a==s==0: break
        reserved.append(dict(address=a,size=s))
    nodes=[]; stack=[]; p=offstruct; end=p+size_struct
    while p+4<=end:
        token=struct.unpack_from('>I',data,p)[0]; p+=4
        if token==1:
            q=data.find(b'\0',p,end)
            if q<0: raise ValueError('unterminated node')
            name=data[p:q].decode('ascii'); p=(q+4)&~3
            path=(stack[-1]['path'].rstrip('/')+'/'+name) if stack else '/'
            n=dict(path=path,offset=p,properties={}); nodes.append(n);stack.append(n)
        elif token==2:
            if not stack: raise ValueError('unbalanced FDT')
            stack.pop()
        elif token==3:
            if p+8>end or not stack: raise ValueError('invalid FDT property')
            length,nameoff=struct.unpack_from('>II',data,p);p+=8
            q=strings.find(b'\0',nameoff)
            if q<0 or p+length>end: raise ValueError('FDT property outside block')
            name=strings[nameoff:q].decode('ascii');v=data[p:p+length];p=(p+length+3)&~3
            if name in stack[-1]['properties']: raise ValueError('duplicate FDT property')
            # String properties are identified by name, not the appearance of bytes.
            if name in ['compatible','model','status','device_type','bootargs','pinctrl-names','clock-names','reg-names'] or name.endswith(('-names','-name')):
                value=v.rstrip(b'\0').decode('utf-8').split('\0')
            elif not v: value=True
            elif length%4==0: value=list(struct.unpack('>'+str(length//4)+'I',v))
            else: value={'bytes':v.hex()}
            stack[-1]['properties'][name]=value
        elif token==4: continue
        elif token==9:
            if stack: raise ValueError('unclosed FDT node')
            return dict(total_size=total,reservations=reserved,nodes=nodes)
        else: raise ValueError('invalid FDT token')
    raise ValueError('missing FDT end')

def tree(data):
    if data[:4]==b'\xd0\x0d\xfe\xed': return fdt(data)
    return dict(nodes=dts(data.decode('utf-8-sig')),reservations=[])

def ranges(nodes):
    """Immediate-parent cell geometry. No implicit bus-to-CPU address translation."""
    index={n['path']:n for n in nodes}; result=[]
    for n in nodes:
        p=n['properties']; parent=index.get(n['path'].rsplit('/',1)[0] or '/',{})
        pp=parent.get('properties',{}); ac=pp.get('#address-cells',[2])[0]; sc=pp.get('#size-cells',[1])[0]
        if 'reg' not in p or n['path']=='/': continue
        cells=p['reg']; stride=ac+sc
        if not isinstance(cells,list) or not stride or len(cells)%stride: raise ValueError('invalid reg geometry at '+n['path'])
        for i in range(0,len(cells),stride):
            def combine(v):
                r=0
                for c in v:r=(r<<32)|c
                return r
            result.append(dict(path=n['path'],index=i//stride,address=combine(cells[i:i+ac]),size=combine(cells[i+ac:i+stride]) if sc else None,address_space='parent-bus',line=n.get('line'),compatible=p.get('compatible',[]),status=p.get('status',['okay'])[0],interrupts_raw=p.get('interrupts',[])))
    return result

def firmware(data):
    result=dict(size=len(data),sha256=sha(data),mbr=None,candidates=[])
    if len(data)>=512 and data[510:512]==b'\x55\xaa':
        result['mbr']=[]
        for i in range(4):
            p=data[446+16*i:462+16*i];start,size=struct.unpack_from('<II',p,8)
            if p[4]: result['mbr'].append(dict(index=i+1,type=hex(p[4]),start_lba=start,sectors=size,in_bounds=(start+size)*512<=len(data)))
    for magic,kind in [(b'\xd0\x0d\xfe\xed','fdt'),(b'\x27\x05\x19\x56','uImage'),(b'\x7fELF','elf')]:
        start=0
        while True:
            pos=data.find(magic,start)
            if pos<0:break
            start=pos+len(magic);entry=dict(kind=kind,offset=pos,valid=False)
            try:
                if kind=='fdt': entry.update(total_size=fdt(data[pos:])['total_size'],valid=True)
                elif kind=='uImage':
                    if pos+64>len(data):raise ValueError('short uImage')
                    h=bytearray(data[pos:pos+64]);_,hcrc,stamp,size,load,ep,dcrc=struct.unpack_from('>7I',h)
                    h[4:8]=b'\0'*4;payload=data[pos+64:pos+64+size]
                    entry.update(size=size,timestamp=stamp,os_id=data[pos+28],architecture_id=data[pos+29],image_type_id=data[pos+30],load=hex(load),entry=hex(ep),name=data[pos+32:pos+64].split(b'\0')[0].decode('ascii',errors='replace'),compression=data[pos+31],header_crc_ok=zlib.crc32(h)==hcrc,payload_crc_ok=len(payload)==size and zlib.crc32(payload)==dcrc)
                    entry['valid']=entry['header_crc_ok'] and entry['payload_crc_ok']
                else:
                    if pos+20>len(data): raise ValueError('short ELF')
                    endian={1:'<',2:'>'}.get(data[pos+5])
                    if data[pos+4] not in (1,2) or endian is None: raise ValueError('bad ELF identity')
                    entry.update(elf_class=data[pos+4],machine=struct.unpack_from(endian+'H',data,pos+18)[0],valid=True,validation='identity only; not executable validation')
            except (ValueError,struct.error,UnicodeError) as e:entry['error']=str(e)
            result['candidates'].append(entry)
    return result

def compare(a,b):
    def normalize(nodes):
        result={}
        for n in nodes:
            props={}
            for k,v in n['properties'].items():
                if v is True: raw=b''
                elif isinstance(v,dict): raw=bytes.fromhex(v['bytes'])
                elif all(isinstance(x,str) for x in v): raw=b''.join(x.encode()+b'\0' for x in v)
                else: raw=struct.pack('>'+str(len(v))+'I',*v)
                props[k]=raw.hex()
            result[n['path']]=props
        return result
    ia=normalize(a);ib=normalize(b)
    return [dict(path=k,left=ia.get(k),right=ib.get(k)) for k in sorted(ia.keys()|ib.keys()) if ia.get(k)!=ib.get(k)]

def validate(root):
    import jsonschema
    sources=json.loads((root/'evidence/sources.json').read_text(encoding='utf-8'));findings=json.loads((root/'evidence/findings.json').read_text(encoding='utf-8'));model=json.loads((root/'registers/canonical/hardware.json').read_text(encoding='utf-8'))
    jsonschema.validate(model,json.loads((root/'registers/schemas/hardware.schema.json').read_text(encoding='utf-8')))
    errors=[];warnings=[]
    sourceids={s['id'] for s in sources};fids=set()
    if len(sourceids)!=len(sources):errors.append('duplicate source ID')
    for f in findings:
        if f['id'] in fids:errors.append('duplicate finding '+f['id'])
        fids.add(f['id'])
        if f['confidence'] not in CONFIDENCE:errors.append('invalid confidence '+f['id'])
        if not f.get('evidence'):errors.append('uncited finding '+f['id'])
        for e in f.get('evidence',[]):
            if e['source'] not in sourceids:errors.append('missing source '+e['source'])
        if f.get('hardware_validated') and f.get('validation')!='hardware-observation':errors.append('unsupported hardware validation '+f['id'])
        if f['confidence']=='verified' and f['scope']=='ATM7039S-hardware' and not f.get('hardware_validated'):errors.append('unvalidated target finding '+f['id'])
    from validate_firmware import validate as validate_binary_evidence
    errors.extend(validate_binary_evidence(root))
    from validate_observations import validate as validate_observations
    errors.extend(validate_observations(root))
    ids=set();seen={}
    for block in model['blocks']:
        if block['id'] in ids:errors.append('duplicate block '+block['id'])
        ids.add(block['id'])
        for e in block['evidence']:
            if e['source'] not in sourceids:errors.append('missing source '+e['source'])
        for reg in block['registers']:
            key=(block['id'],reg['offset'])
            if key in seen and seen[key]!=reg['name']:warnings.append('register alias '+str(key))
            seen[key]=reg['name']
            if reg['offset']<0: errors.append('negative offset '+reg['name'])
            if block['size'] is not None and reg['offset']>=block['size']:errors.append('register outside block '+reg['name'])
            for field in reg['fields']:
                for e in field['evidence']:
                    if e['source'] not in sourceids:errors.append('missing field source '+field['name'])
            if reg['confidence']=='verified' and reg['scope']=='ATM7039S-hardware' and not reg.get('hardware_validated'):errors.append('unvalidated target register '+reg['name'])
            for e in reg['evidence']:
                if e['source'] not in sourceids:errors.append('missing register source '+reg['name'])
    for i,a in enumerate(model['blocks']):
        for b in model['blocks'][i+1:]:
            if a['scope']==b['scope'] and a['size'] and b['size'] and max(a['base'],b['base'])<min(a['base']+a['size'],b['base']+b['size']):
                warnings.append('overlap (review shared resources): '+a['id']+' / '+b['id'])
    return dict(errors=errors,warnings=warnings,blocks=len(model['blocks']),registers=sum(len(b['registers']) for b in model['blocks']),findings=len(findings))

def ledger_counts(root):
    load=lambda rel:json.loads((root/rel).read_text(encoding='utf-8'))
    firmware=sum(len(json.loads(p.read_text(encoding='utf-8')).get('components',[])) for p in sorted((root/'evidence/firmware').glob('*.json')) if isinstance(json.loads(p.read_text(encoding='utf-8')),dict))
    stock=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((root/'evidence/firmware').glob('stock-*-inventory.json'))]
    stock_files=sum(1 for m in stock for part in m['partitions'] for f in part['files'] if f.get('type')=='file')
    return dict(stock_releases=len(stock),stock_files=stock_files,
                findings=len(load('evidence/findings.json')),contradictions=len(load('evidence/contradictions.json')),
                sources=len(load('evidence/sources.json')),files=len(load('evidence/files.json')),firmware_components=firmware,
                predictions=len(load('evidence/predictions.json')),observations=len(load('evidence/observations.json')))

def readme_counts(root):
    """README text with the generated ledger-count block refreshed."""
    text=(root/'README.md').read_text(encoding='utf-8');start,end='<!-- ledger-counts:start -->','<!-- ledger-counts:end -->'
    if start not in text or end not in text:raise ValueError('README.md lacks ledger-count markers')
    c=ledger_counts(root)
    block=(f"Ledger counts, generated by `research.py generate`: **{c['findings']} findings**, {c['contradictions']} contradictions, "
           f"{c['sources']} sources, {c['files']} hashed source files, {c['firmware_components']} catalogued firmware components, "
           f"{c['stock_files']} hashed files from {c['stock_releases']} Anbernic stock images, "
           f"{c['predictions']} pre-registered predictions and {c['observations']} hardware observation records. "
           "Counts measure evidence products, not silicon coverage.")
    head,rest=text.split(start,1);_,tail=rest.split(end,1)
    return head+start+'\n'+block+'\n'+end+tail

def generate(root,check=False):
    model=json.loads((root/'registers/canonical/hardware.json').read_text(encoding='utf-8')); out={}
    lines=['# Source-observed address and register reference','','Generated from `registers/canonical/hardware.json`. These are software observations and related-chip candidates; no hardware validation is claimed. Sizes are DT resources or explicit header extents, never proof of implemented registers.','','| Block | Base | Resource size | Scope | Status | Registers |','|---|---|---|---|---|---|']
    import io
    csvout=io.StringIO();writer=csv.writer(csvout,lineterminator="\n");writer.writerow(['block','scope','base','resource_size','register','offset','address','width','access','reset','confidence','fields','evidence'])
    h=['/* SPDX-License-Identifier: MIT */','/* Generated related-chip candidates. NOT validated ATM7039S constants. */','#ifndef ACTIONS_RESEARCH_CANDIDATES_H','#define ACTIONS_RESEARCH_CANDIDATES_H']
    for b in model['blocks']:
        lines.append(f"| {b['id']} | `0x{b['base']:08x}` | {hex(b['size']) if b['size'] is not None else 'unknown'} | {b['scope']} | {b['status']} | {len(b['registers'])} |")
    for b in model['blocks']:
        lines+=['',f"## {b['id']}",'',b['notes'],'', 'Evidence: '+', '.join(f"{e['source']}:{e.get('path','')}:{e.get('line_start','')}" for e in b['evidence']), '', 'Interrupt cells (raw): `'+str(b['interrupts_raw'])+'`. Dependencies: '+b['dependencies'], '', '| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |','|---|---|---|---|---|---|---|']
        for r in b['registers']:
            lines.append(f"| {r['name']} | `0x{r['offset']:x}` | {r['width'] or 'unknown'} | {r['access']} | {r['reset'] if r['reset'] is not None else 'unknown'} | {r['confidence']} / {r['scope']} | {r['evidence'][0].get('line_start','')} |")
            for field in r['fields']:
                lines.append(f"| ↳ {field['name']} | mask `0x{field['mask']:x}` | — | unknown on target | unknown | {field['confidence']} / {field['scope']} | {field['evidence'][0].get('line_start','')} |")
            writer.writerow([b['id'],b['scope'],hex(b['base']),hex(b['size']) if b['size'] is not None else '',r['name'],hex(r['offset']),hex(b['base']+r['offset']),r['width'],r['access'],r['reset'],r['confidence'],json.dumps(r['fields']),json.dumps(r['evidence'])])
            macro=re.sub(r'\W','_',b['id']+'_'+r['name']).upper()
            h.append(f'#define CANDIDATE_{macro} 0x{b["base"]+r["offset"]:08x}u')
    h+=['#endif',''];out['registers/generated/reference.md']='\n'.join(lines)+'\n';out['registers/generated/registers.csv']=csvout.getvalue();out['registers/generated/candidates.h']='\n'.join(h)
    out['README.md']=readme_counts(root)
    for name,content in out.items():
        p=root/name
        if check:
            if not p.exists() or p.read_text(encoding='utf-8')!=content:raise ValueError('stale generated output: '+name)
        else:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content, encoding='utf-8')
    return list(out)

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    for cmd in ['tree','constants','firmware']:
        q=s.add_parser(cmd);q.add_argument('input',type=Path);q.add_argument('output',type=Path)
    q=s.add_parser('compare');q.add_argument('left',type=Path);q.add_argument('right',type=Path);q.add_argument('output',type=Path)
    s.add_parser('validate');q=s.add_parser('generate');q.add_argument('--check',action='store_true')
    a=p.parse_args()
    try:
        if a.cmd in ['tree','constants','firmware']:
            if not a.input.is_file():raise ValueError('input must be a regular file')
            if a.input.stat().st_size>512*1024*1024:raise ValueError('input exceeds 512 MiB; extract components first')
            data=a.input.read_bytes()
            if a.cmd=='tree':r=tree(data);r['ranges']=ranges(r['nodes'])
            elif a.cmd=='constants':r=constants(data.decode(),str(a.input))
            else:r=firmware(data)
            r['input_sha256']=sha(data);save(a.output,r)
        elif a.cmd=='compare':save(a.output,compare(json.loads(a.left.read_text(encoding='utf-8'))['nodes'],json.loads(a.right.read_text(encoding='utf-8'))['nodes']))
        elif a.cmd=='generate':print('\n'.join(generate(ROOT,a.check)))
        else:
            result=validate(ROOT);print(json.dumps(result,indent=2));return bool(result['errors'])
    except (ValueError,OSError,UnicodeError,KeyError,struct.error) as e:p.error(str(e))
    return 0

if __name__=='__main__':sys.exit(main())
