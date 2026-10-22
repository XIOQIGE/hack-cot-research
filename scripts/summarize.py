"""Aggregate raw JSONL logs into per-method/model ASR tables (Wilson 95% CI)."""
import glob
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def load(paths):
    recs = {}
    for p in paths:
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if r.get("superseded"):
                continue
            recs[(r["case"], r["model"], r["rep"])] = r  # later files override reruns
    return list(recs.values())


def main():
    paths = sys.argv[1:] or sorted(glob.glob(str(ROOT / "logs" / "raw_*.jsonl")))
    recs = load(paths)
    agg = defaultdict(lambda: {"n": 0, "k": 0, "ctrl_k": 0, "err": 0, "empty": 0})
    for r in recs:
        key = (r["method"], r["model"])
        v = r["verdict"]
        if v.get("success") is None:
            agg[key]["err"] += 1
            continue
        a = agg[key]
        a["n"] += 1
        a["k"] += int(bool(v["success"]))
        a["ctrl_k"] += int(bool(r.get("control_verdict", {}).get("success")))
        a["empty"] += int(bool(r["attack"].get("empty_output")))
    lines = ["| 方法 | 模型 | 攻击成功 k/n | ASR | 95% CI | 对照组\"成功\" | 空响应 | 错误 |",
             "|---|---|---|---|---|---|---|---|"]
    for (m, mod), a in sorted(agg.items()):
        lo, hi = wilson(a["k"], a["n"])
        asr = a["k"] / a["n"] if a["n"] else 0
        lines.append(f"| {m} | {mod} | {a['k']}/{a['n']} | {asr:.0%} | [{lo:.0%}, {hi:.0%}] "
                     f"| {a['ctrl_k']}/{a['n']} | {a['empty']} | {a['err']} |")
    table = "\n".join(lines)
    print(table)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "asr_table.md").write_text(table + "\n", encoding="utf-8")
    import csv
    with (ROOT / "results" / "all_records.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case", "method", "model", "rep", "success", "control_success",
                    "attack_empty", "attack_policy_block", "attack_out_tokens", "verdict"])
        for r in sorted(recs, key=lambda r: (r["case"], r["model"], r["rep"])):
            w.writerow([r["case"], r["method"], r["model"], r["rep"], r["verdict"].get("success"),
                        r.get("control_verdict", {}).get("success"),
                        r["attack"].get("empty_output"), r["attack"].get("policy_block"),
                        r["attack"].get("usage", {}).get("output_tokens"),
                        json.dumps(r["verdict"], ensure_ascii=False)])


if __name__ == "__main__":
    main()
