#!/usr/bin/env python3
"""Read GGUF metadata/tensor directory only; no tensor allocation or inference."""
import hashlib, json, os, struct, sys
path=sys.argv[1]
f=open(path,'rb')
def unpack(fmt): return struct.unpack('<'+fmt,f.read(struct.calcsize('<'+fmt)))[0]
def string(): return f.read(unpack('Q')).decode('utf-8')
formats={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
def value(t,keep=True):
    if t==8:
        n=unpack('Q')
        if keep:return f.read(n).decode('utf-8')
        f.seek(n,1);return None
    if t==9:
        ty,n=unpack('I'),unpack('Q')
        if ty in formats and not keep:f.seek(struct.calcsize('<'+formats[ty])*n,1);return None
        out=[]
        for _ in range(n):
            v=value(ty,keep)
            if keep:out.append(v)
        return out if keep else None
    return unpack(formats[t])
magic=f.read(4);assert magic==b'GGUF',magic
version,n_tensors,n_kv=unpack('I'),unpack('Q'),unpack('Q')
meta={}
for _ in range(n_kv):
    key=string();ty=unpack('I')
    keep=not key.startswith('tokenizer.')
    v=value(ty,keep)
    if keep:meta[key]=v
selected=[]
for _ in range(n_tensors):
    name=string();dims=[unpack('Q') for _ in range(unpack('I'))];ty=unpack('I');offset=unpack('Q')
    if name.startswith('blk.64.'):
        selected.append(dict(name=name,shape=dims,ggml_type=ty,relative_offset=offset))
header_end=f.tell()
f.seek(0);header_sha=hashlib.sha256(f.read(header_end)).hexdigest()
print(json.dumps(dict(path=path,size=os.stat(path).st_size,gguf_version=version,tensor_count=n_tensors,metadata_count=n_kv,metadata=meta,tensor_directory_end=header_end,header_sha256=header_sha,blk64_tensors=selected,blk64_count=len(selected),nextn_count=sum('.nextn.' in x['name'] for x in selected),policy='header only; no model load or inference'),indent=2))
