from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import skinny_gate

def good(tp=2):
 lines=[
  "speculative config num_speculative_tokens=3, method=mtp",
  "route map: M=1 N=100000 K=4096 -> qpn2",
  "Ignoring the checkpoint's kv_cache quantization directive",
  "XQA path active",
  "route map: M=8 N=4096 K=4096 -> qpn2",
  "route=qpn8",
 ]
 lines += [f"QPN8_CENSUS_LOAD rank={i%tp} eligible=YES" for i in range(128*tp)]
 return "\\n".join(lines)

class SkinnyGateTests(unittest.TestCase):
 def test_tp2_expected_census_is_256(self):
  r=skinny_gate.evaluate(good(),tp=2,depth=3)
  self.assertTrue(r["pass"])
  item=next(x for x in r["checks"] if x["name"]=="qpn8_census")
  self.assertIn("expected=256",item["detail"])
 def test_upstream_tp4_count_is_not_accepted_as_tp2(self):
  self.assertFalse(skinny_gate.evaluate(good(tp=4),tp=2,depth=3)["pass"])
 def test_fallback_is_failure(self):
  self.assertFalse(skinny_gate.evaluate(good()+"\\nfalling back to requant pack",tp=2,depth=3)["pass"])
if __name__=="__main__":unittest.main()
