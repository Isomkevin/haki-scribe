"""
Run the CodeSwitch ASR benchmark over test-clips/.

Usage (from hakiscribe-backend/):
  python -m benchmarking.run_benchmark

Writes:
  benchmarking/out/benchmark_report.json
  benchmarking/out/BENCHMARK_RESULTS.md
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Allow `python -m benchmarking.run_benchmark` from hakiscribe-backend/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarking.metrics.entities import entity_accuracy
from benchmarking.metrics.wer_cer import cer, wer
from benchmarking.providers import benchmark_providers


CLIPS_DIR = Path(__file__).resolve().parent / "test-clips"
OUT_DIR = Path(__file__).resolve().parent / "out"


@dataclass
class BenchmarkClip:
    clip_id: str
    meta: dict
    audio_path: Path
    reference: str
    key_terms: list[str] = field(default_factory=list)

    @property
    def language_hint(self) -> str | None:
        pair = self.meta.get("language_pair", "")
        if pair == "en-sw":
            return "code-switch"
        if pair.startswith("en-"):
            return "multilingual"
        return self.meta.get("language_hint")


def load_clips(directory: Path = CLIPS_DIR) -> list[BenchmarkClip]:
    clips: list[BenchmarkClip] = []
    for meta_path in sorted(directory.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        clip_id = meta.get("clip_id") or meta_path.stem.replace(".meta", "")
        ref_name = meta.get("reference_transcript_path") or f"{clip_id}.reference.txt"
        ref_path = directory / ref_name
        reference = ref_path.read_text(encoding="utf-8").strip() if ref_path.exists() else ""
        audio_name = meta.get("audio_file") or f"{clip_id}.webm"
        audio_path = directory / audio_name
        key_terms = list(meta.get("key_terms") or [])
        clips.append(
            BenchmarkClip(
                clip_id=clip_id,
                meta=meta,
                audio_path=audio_path,
                reference=reference,
                key_terms=key_terms,
            )
        )
    return clips


async def run_benchmark(clips: list[BenchmarkClip]) -> dict:
    providers = benchmark_providers()
    rows: list[dict] = []

    for clip in clips:
        if not clip.audio_path.exists():
            for provider in providers:
                rows.append(
                    {
                        "clip_id": clip.clip_id,
                        "provider": provider.name,
                        "skipped": True,
                        "skip_reason": f"audio missing: {clip.audio_path.name}",
                        "meta": clip.meta,
                    }
                )
            continue

        audio_bytes = clip.audio_path.read_bytes()
        filename = clip.audio_path.name
        hint = clip.language_hint

        for provider in providers:
            outcome = await provider.transcribe(audio_bytes, filename, hint)
            if outcome.skipped:
                rows.append(
                    {
                        "clip_id": clip.clip_id,
                        "provider": provider.name,
                        "skipped": True,
                        "skip_reason": outcome.skip_reason,
                        "meta": clip.meta,
                    }
                )
                continue

            hypothesis = outcome.transcript
            rows.append(
                {
                    "clip_id": clip.clip_id,
                    "provider": provider.name,
                    "skipped": False,
                    "wer": round(wer(clip.reference, hypothesis), 4) if clip.reference else None,
                    "cer": round(cer(clip.reference, hypothesis), 4) if clip.reference else None,
                    "entity_accuracy": round(entity_accuracy(clip.key_terms, hypothesis), 4),
                    "latency_ms": outcome.latency_ms,
                    "transcript_preview": hypothesis[:240],
                    "meta": clip.meta,
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clip_count": len(clips),
        "providers": [p.name for p in providers],
        "results": rows,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# HakiScribe ASR Benchmark — Sahara CodeSwitch Africa Challenge",
        "",
        f"Generated: {report.get('generated_at', '')}",
        "",
        "| Clip | Provider | WER | CER | Entity acc. | Latency (ms) | Notes |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report.get("results", []):
        if row.get("skipped"):
            lines.append(
                f"| {row['clip_id']} | {row['provider']} | — | — | — | — | skipped: {row.get('skip_reason', '')} |"
            )
        else:
            wer_v = row.get("wer")
            cer_v = row.get("cer")
            ent = row.get("entity_accuracy")
            lines.append(
                f"| {row['clip_id']} | {row['provider']} | {wer_v if wer_v is not None else '—'} | "
                f"{cer_v if cer_v is not None else '—'} | {ent} | {row.get('latency_ms', '—')} | |"
            )
    lines.extend(
        [
            "",
            "## How to run",
            "",
            "```bash",
            "cd hakiscribe-backend",
            "python -m benchmarking.run_benchmark",
            "```",
            "",
            "Place consented `.webm`/`.wav` files and matching `*.meta.json` + reference transcripts under `benchmarking/test-clips/`.",
        ]
    )
    return "\n".join(lines) + "\n"


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clips = load_clips()
    report = await run_benchmark(clips)
    json_path = OUT_DIR / "benchmark_report.json"
    md_path = OUT_DIR / "BENCHMARK_RESULTS.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
