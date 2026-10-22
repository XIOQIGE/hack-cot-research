"""Run a single test case against a target model.

Claude models: the relay only accepts Claude Code clients, so requests go through
`claude -p` with a custom system prompt and no tools; thinking blocks are parsed from stream-json.
GPT models: OpenAI-compatible /v1/chat/completions with a real system message.
"""
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT.parent / ".env.local"  # kept outside the repo, never committed


def load_env():
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    env["ANTHROPIC_BASE_URL"] = env.get("LS_BASE_URL", env.get("ANTHROPIC_BASE_URL", ""))
    env["ANTHROPIC_AUTH_TOKEN"] = env.get("LS_API_KEY", env.get("ANTHROPIC_AUTH_TOKEN", ""))
    env["MAX_THINKING_TOKENS"] = env.get("MAX_THINKING_TOKENS", "8000")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def call_model(model, system, prompt, timeout=600, retries=4):
    """Retry relay/infra errors (e.g. intermittent 403 billing_error from a pooled account)."""
    once = _call_gpt if model.startswith("gpt-") else _call_once
    for attempt in range(retries + 1):
        out = once(model, system, prompt, timeout)
        if not out["error"]:
            break
        time.sleep(5 * (attempt + 1))
    out["attempts"] = attempt + 1
    return out


def _call_gpt(model, system, prompt, timeout):
    """OpenAI-compatible chat/completions. trust_env=False: the local system proxy breaks TLS to the relay.
    GPT-6 Astra hides raw CoT; only a reasoning summary (reasoning_content) and reasoning_tokens are returned."""
    import httpx
    env = load_env()
    out = {"model": model, "thinking": "", "text": "", "usage": {}, "cost": None, "error": None,
           "redacted_thinking": 0, "backend": "chat_completions"}
    t0 = time.time()
    try:
        r = httpx.post(env["LS_BASE_URL"] + "/v1/chat/completions", timeout=timeout, trust_env=False,
                       headers={"Authorization": "Bearer " + env["GPT_API_KEY"]},
                       json={"model": model, "reasoning_effort": env.get("GPT_REASONING_EFFORT", "high"),
                             "messages": [{"role": "system", "content": system},
                                          {"role": "user", "content": prompt}]})
        d = r.json()
        if r.status_code != 200 or "choices" not in d:
            out["error"] = f"HTTP {r.status_code}: {str(d)[:300]}"
        else:
            ch = d["choices"][0]
            out["text"] = ch["message"].get("content") or ""
            out["thinking"] = ch["message"].get("reasoning_content") or ""
            out["stop_reason"] = ch.get("finish_reason")
            u = d.get("usage", {})
            out["usage"] = {"input_tokens": u.get("prompt_tokens"),
                            "output_tokens": u.get("completion_tokens"),
                            "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens")}
    except Exception as e:  # network-level failure -> retried
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    out["latency_s"] = round(time.time() - t0, 2)
    out["empty_output"] = not out["text"] and not out["error"]
    out["policy_block"] = False
    return out


def _call_once(model, system, prompt, timeout):
    cmd = ["claude", "-p", "--model", model, "--system-prompt", system,
           "--tools", "", "--output-format", "stream-json", "--verbose",
           "--max-turns", "1"]
    t0 = time.time()
    proc = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True,
                          env=load_env(), timeout=timeout, cwd=str(ROOT / "scratch"))
    out = {"model": model, "thinking": "", "text": "", "usage": {}, "cost": None,
           "error": None, "latency_s": round(time.time() - t0, 2), "redacted_thinking": 0}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "assistant":
            for b in d["message"].get("content", []):
                if b.get("type") == "thinking":
                    out["thinking"] += b.get("thinking", "")
                elif b.get("type") == "redacted_thinking":
                    out["redacted_thinking"] += 1
                elif b.get("type") == "text":
                    out["text"] += b.get("text", "")
        elif d.get("type") == "result":
            out["usage"] = d.get("usage", {})
            out["cost"] = d.get("total_cost_usd")
            out["stop_reason"] = d.get("stop_reason")
            if d.get("is_error"):
                out["error"] = d.get("result")
    # An empty end_turn is a genuine model behaviour (the model chose to say nothing), not a failure.
    out["empty_output"] = not out["text"] and not out["thinking"]
    if out["empty_output"] and not out["error"] and out.get("stop_reason") != "end_turn":
        out["error"] = proc.stderr.decode("utf-8", "replace")[-500:] or "no result"
    # The CLI surfaces API failures as assistant text; separate infra errors from policy refusals.
    out["policy_block"] = "violate our Usage Policy" in out["text"]
    if not out["policy_block"] and out["text"].lstrip().startswith(("API Error", "Failed to authenticate")):
        out["error"] = out["text"][:300]
    return out
