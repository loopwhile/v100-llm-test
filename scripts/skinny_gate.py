#!/usr/bin/env python3
"""Validate the v100-skinny boot/runtime witnesses needed before measurements."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path

def evaluate(text: str, *, tp: int, depth: int) -> dict:
    checks=[]
    def add(name, ok, detail=""): checks.append({"name":name,"ok":bool(ok),"detail":detail})
    m=re.search(r"num_speculative_tokens[^,}\n]*?(\d+)",text)
    served=int(m.group(1)) if m else None
    add("served_depth",served==depth,str(served))
    lm_routes=set(re.findall(r"route map: M=\d+ N=\d{5,} K=\d+ -> ([a-z0-9]+)",text))
    add("lm_head_qpn",bool(lm_routes) and any(x.startswith("qpn") for x in lm_routes),",".join(sorted(lm_routes)))
    fallback=("falling back to requant pack" in text or "packing from the model's own weights" in text)
    add("no_lm_head_repack_fallback",not fallback)
    add("fp16_kv_directive_declined","Ignoring the checkpoint's kv_cache quantization directive" in text)
    scalar=text.count("scalar_paged"); add("zero_scalar_paged",scalar==0,str(scalar))
    add("xqa_active","XQA path active" in text)
    add("qpn2_dispatch",re.search(r"route map: M=\d+ N=\d+ K=\d+ -> qpn2",text) is not None)
    census=len(re.findall(r"QPN8_CENSUS_LOAD",text))
    ineligible=len(re.findall(r"QPN8_CENSUS_LOAD.*eligible=NO",text))
    expected=128*tp
    add("qpn8_census",census==expected and ineligible==0,f"census={census} expected={expected} ineligible={ineligible}")
    add("qpn8_dispatch","route=qpn8" in text)
    return {"pass":all(x["ok"] for x in checks),"tp":tp,"depth":depth,"checks":checks}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log",type=Path,required=True);ap.add_argument("--tp",type=int,default=2)
    ap.add_argument("--depth",type=int,default=3);a=ap.parse_args()
    if a.tp<1 or a.depth<1: raise SystemExit("tp/depth must be positive")
    result=evaluate(a.log.read_text(errors="replace"),tp=a.tp,depth=a.depth)
    print(json.dumps(result,indent=2))
    return 0 if result["pass"] else 2
if __name__=="__main__":raise SystemExit(main())
