"""Run all cases: control + attack, each target model, N repetitions.
Usage: python run_all.py [--reps 3] [--models a,b] [--only M1,M2]
Writes raw JSONL to logs/raw_<timestamp>.jsonl and a summary CSV to results/."""
import argparse
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cases import CASES
from judge import judge
from runner import ROOT, call_model

DEFAULT_MODELS = ["claude-opus-5-5", "claude-fable-5-1"]


def run_one(case, model, rep):
    ctrl = call_model(model, case["system"], case["control"])
    atk = call_model(model, case["system"], case["attack"])
    rec = {"case": case["id"], "method": case["method"], "model": model, "rep": rep,
           "system": case["system"], "control_prompt": case["control"],
           "attack_prompt": case["attack"], "control": ctrl, "attack": atk,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if ctrl["error"] or atk["error"]:
        rec["verdict"] = {"success": None, "error": ctrl["error"] or atk["error"]}
    else:
        rec["verdict"] = judge(case, ctrl, atk)
        rec["control_verdict"] = judge(case, ctrl, ctrl)  # does the control already "succeed"?
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--rep-start", type=int, default=0)
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    cases = [c for c in CASES if not a.only or c["id"].split("-")[0] in a.only.split(",")]
    jobs = [(c, m, r) for c in cases for m in a.models.split(",") for r in range(a.rep_start, a.rep_start + a.reps)]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "results").mkdir(exist_ok=True)
    raw = ROOT / "logs" / f"raw_{stamp}.jsonl"
    rows = []
    with ThreadPoolExecutor(a.workers) as ex, raw.open("w", encoding="utf-8") as f:
        for rec in ex.map(lambda j: run_one(*j), jobs):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            v = rec["verdict"]
            print(rec["case"], rec["model"], rec["rep"], "success=", v.get("success"),
                  {k: v[k] for k in v if k != "success"})
            rows.append({"case": rec["case"], "method": rec["method"], "model": rec["model"],
                         "rep": rec["rep"], "success": v.get("success"),
                         "control_success": rec.get("control_verdict", {}).get("success"),
                         "details": json.dumps(v, ensure_ascii=False)})
    with (ROOT / "results" / f"summary_{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("raw log:", raw)


if __name__ == "__main__":
    main()
