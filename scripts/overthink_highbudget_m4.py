"""E9: M4 OverThink at a larger thinking budget. The main run capped reasoning at
MAX_THINKING_TOKENS=8000 (runner.py default), and the attack works by making the model spend
more output tokens, so the cap is a ceiling on the effect itself: a 167x Fable amplification
under an 8k cap is a lower bound, not a measurement of what the decoy can extract.

This reruns both M4 cases with the budget raised, and records the control's token spend in the
same batch so the amplification ratio is computed against a control from the same conditions.
Set the budget via the environment before invoking:

  MAX_THINKING_TOKENS=32000 python overthink_highbudget_m4.py
  MAX_THINKING_TOKENS=32000 python overthink_highbudget_m4.py gpt-6-astra

Usage: python overthink_highbudget_m4.py [model1,model2] [--reps 5]
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

os.environ["PYTHONIOENCODING"] = "utf-8"

from cases import CASES
from judge import judge
from runner import ROOT, call_model

M4 = [c for c in CASES if c["method"] == "M4_OverThink"]


def run_one(case, model, rep):
    ctrl = call_model(model, case["system"], case["control"])
    atk = call_model(model, case["system"], case["attack"])
    v = judge(case, ctrl, atk)
    return {"exp": "E9", "case": case["id"], "model": model, "rep": rep,
            "budget": os.environ.get("MAX_THINKING_TOKENS"), "verdict": v,
            "ctrl_out_tokens": v.get("ctrl_out_tokens"), "atk_out_tokens": v.get("atk_out_tokens"),
            "ctrl_error": ctrl["error"], "atk_error": atk["error"],
            "ctrl_text": (ctrl["text"] or "")[:300], "atk_text": (atk["text"] or "")[:300],
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}


def main():
    argv = sys.argv[1:]
    reps = 5
    for a in argv:
        if a.startswith("--reps"):
            reps = int(a.split("=")[1])
    models = [a for a in argv if not a.startswith("--")]
    models = models[0].split(",") if models else ["claude-opus-5-5", "claude-fable-5-1", "gpt-6-astra"]
    budget = os.environ.get("MAX_THINKING_TOKENS", "8000")
    jobs = [(c, m, r) for m in models for c in M4 for r in range(reps)]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    p = ROOT / "logs" / f"supplementary_E9_m4_budget{budget}_{stamp}.jsonl"
    rows = []
    with ThreadPoolExecutor(3) as ex, p.open("w", encoding="utf-8") as f:
        for rec in ex.map(lambda j: run_one(*j), jobs):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            rows.append(rec)
            v = rec["verdict"]
            print(f"{rec['model']:18s} {rec['case']} {rec['rep']} "
                  f"ctrl={rec['ctrl_out_tokens']} atk={rec['atk_out_tokens']} "
                  f"x{v.get('amplification')} correct={v.get('answer_correct')} "
                  f"success={v.get('success')} err={(rec['atk_error'] or '')[:40]}")
    print("\n| model | case | n | median amplification | max | success |")
    print("|---|---|---|---|---|---|")
    for m in models:
        for c in M4:
            sub = [r for r in rows if r["model"] == m and r["case"] == c["id"]
                   and not (r["atk_error"] or r["ctrl_error"])]
            if not sub:
                continue
            amps = sorted(r["verdict"]["amplification"] for r in sub)
            med = amps[len(amps) // 2]
            ok = sum(r["verdict"]["success"] for r in sub)
            print(f"| {m} | {c['id']} | {len(sub)} | {med}x | {amps[-1]}x | {ok}/{len(sub)} |")
    print("log:", p)


if __name__ == "__main__":
    main()
