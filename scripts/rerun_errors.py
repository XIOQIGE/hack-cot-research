"""Re-run only records whose verdict is an infra error (success=None) across all raw logs.
Output goes to a new raw_rerun_*.jsonl; summarize.py lets later files override earlier ones."""
import glob
import json
import time
from cases import CASES
from run_all import run_one
from runner import ROOT

C = {c["id"]: c for c in CASES}
latest = {}
for p in sorted(glob.glob(str(ROOT / "logs" / "raw_*.jsonl"))):
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        latest[(r["case"], r["model"], r["rep"])] = r
todo = [k for k, r in latest.items() if r["verdict"].get("success") is None]
print("rerunning", len(todo))
out = ROOT / "logs" / f"raw_rerun_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
with out.open("w", encoding="utf-8") as f:
    for cid, model, rep in todo:
        rec = run_one(C[cid], model, rep)
        rec["rerun"] = True
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        print(cid, model, rep, rec["verdict"].get("success"), rec["verdict"].get("error", "")[:80])
print("log:", out)
