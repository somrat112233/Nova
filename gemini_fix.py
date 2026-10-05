from langchain_openai import ChatOpenAI

DUMMY = "skip_thought_signature_validator"
_orig = ChatOpenAI._get_request_payload


def _patched(self, *args, **kwargs):
    payload = _orig(self, *args, **kwargs)
    base = str(getattr(self, "openai_api_base", "") or "")
    if "googleapis.com" in base:
        for m in payload.get("messages", []):
            if m.get("role") == "assistant":
                for tc in m.get("tool_calls") or []:
                    tc.setdefault("extra_content", {"google": {"thought_signature": DUMMY}})
    return payload


ChatOpenAI._get_request_payload = _patched


import os, time, urllib.request

_orig_gen = ChatOpenAI._generate
TRANSIENT = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "rate_limit", "Rate limit", "overloaded")


def _transient(e):
    return any(x in str(e) for x in TRANSIENT)


def _alternatives():
    alts = []
    if os.getenv("GROQ_API_KEY"):
        alts.append(("groq", "https://api.groq.com/openai/v1", os.getenv("GROQ_API_KEY"),
                     os.getenv("AGENT_GROQ_MODEL", "openai/gpt-oss-120b")))
    if os.getenv("OPENROUTER_API_KEY") and os.getenv("AGENT_OPENROUTER_MODEL"):
        alts.append(("openrouter", "https://openrouter.ai/api/v1", os.getenv("OPENROUTER_API_KEY"),
                     os.getenv("AGENT_OPENROUTER_MODEL")))
    if os.getenv("AGENT_FAILOVER_LOCAL") == "1":
        try:
            urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2)
            alts.append(("local", "http://127.0.0.1:8080/v1", "none", "local"))
        except Exception:
            pass
    return alts


def _retry_gen(self, *a, **k):
    base = str(getattr(self, "openai_api_base", "") or "")
    if "googleapis.com" not in base:
        return _orig_gen(self, *a, **k)
    last = None
    for d in (0, 5, 10, 20):
        if d:
            time.sleep(d)
        try:
            return _orig_gen(self, *a, **k)
        except Exception as e:
            if not _transient(e):
                raise
            last = e
    main = self.model_name
    fb = os.getenv("AGENT_GEMINI_FALLBACK", "gemini-3.5-flash")
    if fb and fb != main:
        self.model_name = fb
        try:
            return _orig_gen(self, *a, **k)
        except Exception as e:
            if not _transient(e):
                raise
            last = e
        finally:
            self.model_name = main
    for name, url, key, model in _alternatives():
        try:
            alt = ChatOpenAI(model=model, base_url=url, api_key=key,
                             max_tokens=getattr(self, "max_tokens", None) or 2048)
            print(f"[failover -> {name}]")
            return _orig_gen(alt, *a, **k)
        except Exception as e:
            last = e
    raise last


ChatOpenAI._generate = _retry_gen
