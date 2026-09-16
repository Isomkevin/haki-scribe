"""One-off validation for demo_catalog timings/flags."""
from app.services.demo_catalog import SESSIONS, SAHARA_DEMO_TITLES

print("sessions", len(SESSIONS))
issues = []
for s in SESSIONS:
    segs = s["segments"]
    end = max(x["end_ms"] for x in segs)
    for f in s.get("flags") or []:
        if f["at_ms"] > end:
            issues.append(f"{s['title'][:50]}: flag {f['at_ms']} > end {end}")
    for i in s.get("redact_indexes") or []:
        if i >= len(segs):
            issues.append(f"{s['title'][:50]}: redact {i} out of range {len(segs)}")
    if not s.get("generate"):
        issues.append(f"{s['title'][:50]}: generate False")
    for i, seg in enumerate(segs):
        if seg["end_ms"] <= seg["start_ms"]:
            issues.append(f"bad dur {s['title'][:30]} #{i}")
    print(f"  {len(segs):2d} segs  {end/1000:6.1f}s  gen={s.get('generate')}  {s['title'][:64]}")

sahara_ok = all(any(x["title"] == t for x in SESSIONS) for t in SAHARA_DEMO_TITLES)
print("sahara titles in catalog", sahara_ok)
print("issues", issues or "none")
