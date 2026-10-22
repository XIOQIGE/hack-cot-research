"""E0: model provenance check. Which routes really serve the model they claim to be?
Fingerprints: response id prefix, token count of a fixed probe, reasoning style, self-identification."""
import json
import time
import httpx
from runner import ROOT, call_model, load_env

PROBE = "Pseudopseudohypoparathyroidism 量子纠缠 ZX-CANARY-4471 αβγ " * 20
ID_Q = "Which company trained you and which model family are you? One line."


def direct_messages(env, model, text):
    r = httpx.post(env["LS_BASE_URL"] + "/v1/messages", timeout=300, trust_env=False,
                   headers={"x-api-key": env["GPT_API_KEY"], "anthropic-version": "2023-06-01"},
                   json={"model": model, "max_tokens": 1500, "messages": [{"role": "user", "content": text}],
                         "thinking": {"type": "enabled", "budget_tokens": 1024}})
    d = r.json()
    return {"id": d.get("id"), "model": d.get("model"), "usage": d.get("usage"),
            "thinking": "".join(b.get("thinking", "") for b in d.get("content", []) if b.get("type") == "thinking"),
            "text": "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")}


def total_in(u):
    """Billed input excludes cache hits; add them back so routes are comparable."""
    u = u or {}
    return sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def gpt_regimes(env, reps=6):
    """The GPT route mixes backends: some calls carry a ~4.4k-token hidden upstream prompt, some none."""
    c = httpx.Client(trust_env=False, timeout=300)
    rows = []
    for rep in range(reps):
        for sysmsg in (None, "You are a helpful assistant."):
            msgs = [{"role": "system", "content": sysmsg}] if sysmsg else []
            rec = {"exp": "E0b", "rep": rep, "system": bool(sysmsg)}
            for key, text in (("hi", "hi"), ("probe", "hi " + PROBE), ("ident", ID_Q)):
                try:
                    r = c.post(env["LS_BASE_URL"] + "/v1/chat/completions",
                               headers={"Authorization": "Bearer " + env["GPT_API_KEY"]},
                               json={"model": "gpt-6-astra", "reasoning_effort": "low",
                                     "messages": msgs + [{"role": "user", "content": text}]}).json()
                    rec[key + "_in"] = r["usage"]["prompt_tokens"]
                    rec[key + "_id"] = r.get("id", "")[:14]
                    if key == "ident":
                        rec["identity"] = (r["choices"][0]["message"].get("content") or "")[:200]
                except Exception as e:
                    rec[key + "_error"] = str(e)[:200]
            rows.append(rec)
            print(json.dumps(rec, ensure_ascii=False))
    return rows


def main(reps=3):
    env = load_env()
    rows = []
    for name, fn in [
        ("cli_claude-opus-5-5", lambda t: call_model("claude-opus-5-5", "You are a helpful assistant.", t)),
        ("cli_claude-fable-5-1", lambda t: call_model("claude-fable-5-1", "You are a helpful assistant.", t)),
        ("direct_messages_claude-opus-5-5(GPT key)", lambda t: direct_messages(env, "claude-opus-5-5", t)),
        ("chat_gpt-6-astra", lambda t: call_model("gpt-6-astra", "You are a helpful assistant.", t)),
    ]:
        for rep in range(reps):
            try:
                ident, short, long_ = fn(ID_Q), fn("hi"), fn("hi " + PROBE)
                hi, pr = total_in(short.get("usage")), total_in(long_.get("usage"))
                rec = {"route": name, "rep": rep, "identity_answer": ident["text"][:300],
                       "thinking_sample": ident["thinking"][:600], "response_id": ident.get("id"),
                       "in_tokens_hi": hi, "in_tokens_probe": pr, "probe_delta": pr - hi,
                       "usage_hi": short.get("usage"), "usage_probe": long_.get("usage")}
            except Exception as e:
                rec = {"route": name, "rep": rep, "error": str(e)[:300]}
            rows.append(rec)
            print(json.dumps({k: rec.get(k) for k in ("route", "rep", "identity_answer", "in_tokens_hi",
                                                     "in_tokens_probe", "probe_delta", "error")},
                             ensure_ascii=False))
    out = ROOT / "logs" / f"supplementary_E0_provenance_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print("log:", out)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["regimes"]:
        rows = gpt_regimes(load_env())
        out = ROOT / "logs" / f"supplementary_E0b_gpt_regimes_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print("log:", out)
    else:
        main()
