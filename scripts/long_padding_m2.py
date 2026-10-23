"""M2 long-padding rerun. Same cases, fixed heavy thinking budget, per-condition reasoning length.

Why this exists: the original M2 payload was ~250 words, so reasoning models finished it in
1-2k output tokens. Refusal dilution depends on the benign reasoning being much longer than
that. This rerun uses a 10-problem chain and records reasoning length per condition, so the
"was the dose actually large enough" question can be answered from the log itself.

Usage: python long_padding_m2.py [model1,model2] [--reps 5]
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

os.environ["PYTHONIOENCODING"] = "utf-8"

from cases_long import LONG_CASES
from runner import ROOT, call_model, load_env

BUDGET = "32000"


def run_one(case, model, rep):
    env_note = {"thinking_budget": BUDGET}
    atk = call_model(model, case["system"], case["attack"])
    rec = {"case": case["id"], "method": case["method"], "model": model, "rep": rep,
           "cond": case.get("cond"), "system": case["system"], "attack_prompt": case["attack"],
           "attack": atk, "meta": env_note, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if atk["error"]:
        rec["verdict"] = {"success": None, "error": atk["error"]}
    else:
        from judge import has_canary
        u = atk["usage"] or {}
        rec["verdict"] = {
            "success": has_canary(atk["text"]),
            "canary_in_thinking": has_canary(atk["thinking"]),
            "output_tokens": u.get("output_tokens"),
            "reasoning_tokens": u.get("reasoning_tokens"),
            "empty_output": atk["empty_output"],
        }
    return rec


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reps = 5
    for a in sys.argv[1:]:
        if a.startswith("--reps"):
            reps = int(a.split("=")[1])
    models = args[0].split(",") if args else ["claude-opus-5-5", "claude-fable-5-1", "gpt-6-astra"]
    jobs = [(c, m, r) for m in models for c in LONG_CASES for r in range(reps)]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    raw = ROOT / "logs" / f"supplementary_M2long_{stamp}.jsonl"
    rows = []
    with ThreadPoolExecutor(4) as ex, raw.open("w", encoding="utf-8") as f:
        for rec in ex.map(lambda j: run_one(*j), jobs):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            v = rec["verdict"]
            print(rec["cond"], rec["model"], rec["rep"], "success=", v.get("success"),
                  "out_tokens=", v.get("output_tokens"), "reasoning=", v.get("reasoning_tokens"))
            rows.append(rec)
    print("log:", raw)


if __name__ == "__main__":
    main()
