import json
import urllib.error
import urllib.request

BASE = "https://hakiscribe-backend.onrender.com"


def req(method: str, url: str, data=None, timeout: int = 90):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"error": raw[:400]}


def main() -> None:
    status, health = req("GET", f"{BASE}/health", timeout=45)
    print("HEALTH", status)
    print(json.dumps(health.get("integrations", health), indent=2))

    status, news = req(
        "POST",
        f"{BASE}/news/search",
        {"query": "Kenya Law latest Companies Act amendments"},
        timeout=90,
    )
    hits = news.get("hits") or []
    print("NEWS", status, "configured=", news.get("configured"), "hits=", len(hits))
    for index, hit in enumerate(hits[:3], 1):
        title = hit.get("title")
        url = hit.get("url")
        print(f"  {index}. {title}")
        print(f"     {url}")

    print("SHOWCASE starting")
    status, showcase = req("POST", f"{BASE}/demo/showcase", timeout=240)
    print("SHOWCASE", status)
    if not isinstance(showcase, dict):
        print(showcase)
        return
    if showcase.get("detail") and "action_results" not in showcase:
        print(showcase)
        return
    print("title=", showcase.get("title"))
    print("status=", showcase.get("status"))
    results = showcase.get("action_results") or []
    actions = showcase.get("detected_actions") or []
    print("detected=", [item.get("type") for item in actions])
    print("results=", len(results))
    for item in results:
        payload = item.get("result") or {}
        print(
            " -",
            item.get("type"),
            item.get("status"),
            "doc_id=",
            bool(payload.get("ambiguous_document_id")),
            "event_id=",
            bool(payload.get("ambiguous_event_id")),
            "ics=",
            bool(payload.get("ics")),
            "workspace=",
            bool(payload.get("workspace_url")),
            "sources=",
            len(payload.get("sources") or []),
        )


if __name__ == "__main__":
    main()
