"""Hume Expression Measurement Batch API prosody provider (S6 production).

Uses the recorded-audio Batch API with the prosody model — NOT EVI live runtime.
Direct provider evidence: expression labels + timed segments.
Derived acoustic evidence merged from acoustic_derive (numpy/scipy).
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.language_speaking_providers.acoustic_derive import derive_acoustic_prosody
from app.services.language_speaking_providers.capabilities import AcousticFeatureCapabilities
from app.services.language_speaking_providers.providers import AcousticFeatureProvider

logger = logging.getLogger(__name__)
settings = get_settings()

_HUME_BATCH_JOBS_URL = "https://api.hume.ai/v0/batch/jobs"
_HUME_MODEL = "prosody"


def _api_key() -> str:
    return (settings.HUME_API_KEY or "").strip()


def _headers() -> dict[str, str]:
    return {"X-Hume-Api-Key": _api_key()}


def _parse_hume_predictions(payload: Any) -> tuple[list[dict], list[dict]]:
    """Extract expression observations and turn segments from Hume predictions."""
    expressions: list[dict[str, object]] = []
    segments: list[dict[str, object]] = []

    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if not isinstance(item, dict):
            continue
        results = item.get("results") or item
        predictions = results.get("predictions") if isinstance(results, dict) else None
        if not isinstance(predictions, list):
            continue
        for pred in predictions:
            if not isinstance(pred, dict):
                continue
            models = pred.get("models") or {}
            prosody = models.get("prosody") or {}
            grouped = prosody.get("grouped_predictions") or prosody.get("predictions") or []
            if isinstance(grouped, dict):
                grouped = [grouped]
            for group in grouped:
                if not isinstance(group, dict):
                    continue
                inner = group.get("predictions") or [group]
                if not isinstance(inner, list):
                    inner = [inner]
                for seg in inner:
                    if not isinstance(seg, dict):
                        continue
                    time_info = seg.get("time") or {}
                    begin = float(time_info.get("begin") or time_info.get("start") or 0.0)
                    end = float(time_info.get("end") or begin)
                    if end > begin:
                        segments.append(
                            {
                                "start_sec": begin,
                                "end_sec": end,
                                "speaker_id": str(seg.get("speaker_id") or group.get("id") or ""),
                            }
                        )
                    for emo in seg.get("emotions") or []:
                        if not isinstance(emo, dict):
                            continue
                        name = str(emo.get("name") or "")
                        score = float(emo.get("score") or 0.0)
                        if not name:
                            continue
                        expressions.append(
                            {
                                "provider_label": name,
                                "normalized_tag": f"expression:{name.strip().lower().replace(' ', '_')}",
                                "confidence": score,
                                "source": "direct_provider",
                                "segment_start_sec": begin,
                                "segment_end_sec": end,
                            }
                        )
    return expressions, segments


def _submit_and_fetch_sync(audio_bytes: bytes, *, timeout_s: int, poll_s: float) -> dict[str, Any]:
    api_key = _api_key()
    if not api_key:
        raise RuntimeError("HUME_API_KEY is not configured")

    job_config = {"models": {"prosody": {"granularity": "utterance"}}}
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        with httpx.Client(timeout=httpx.Timeout(float(timeout_s))) as client:
            with tmp_path.open("rb") as fh:
                response = client.post(
                    _HUME_BATCH_JOBS_URL,
                    headers=_headers(),
                    data={"json": json.dumps(job_config)},
                    files={"file": (tmp_path.name, fh, "audio/wav")},
                )
            if response.status_code == 401:
                raise PermissionError("Hume authentication failed")
            if response.status_code == 403 and "discontinued" in (response.text or "").lower():
                raise RuntimeError("Hume Expression Measurement API discontinued")
            if response.status_code == 429:
                raise RuntimeError("Hume rate limited")
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Hume batch submit failed: status={response.status_code} detail={response.text[:500]}"
                )
            job_id = str(response.json().get("job_id") or "")
            if not job_id:
                raise RuntimeError("Hume batch submit returned no job_id")

            deadline = time.monotonic() + timeout_s
            status = "QUEUED"
            while time.monotonic() < deadline:
                status_resp = client.get(f"{_HUME_BATCH_JOBS_URL}/{job_id}", headers=_headers())
                if status_resp.status_code >= 400:
                    raise RuntimeError(f"Hume job status failed: {status_resp.status_code}")
                body = status_resp.json()
                state = body.get("state") or {}
                status = str(state.get("status") or body.get("status") or "UNKNOWN").upper()
                if status in {"COMPLETED", "COMPLETE"}:
                    break
                if status in {"FAILED", "ERROR"}:
                    raise RuntimeError(f"Hume job failed: {body}")
                time.sleep(max(0.5, poll_s))

            if status not in {"COMPLETED", "COMPLETE"}:
                raise TimeoutError("Hume batch job timed out")

            pred_resp = client.get(f"{_HUME_BATCH_JOBS_URL}/{job_id}/predictions", headers=_headers())
            if pred_resp.status_code >= 400:
                raise RuntimeError(f"Hume predictions fetch failed: {pred_resp.status_code}")
            return pred_resp.json()
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _analyze_sync(audio_bytes: bytes) -> dict[str, object]:
    timeout = max(1, int(settings.SPEAKING_PROSODY_TIMEOUT_SECONDS or 120))
    poll = max(0.5, float(settings.SPEAKING_PROSODY_POLL_INTERVAL_SECONDS or 2.0))
    warnings: list[str] = []
    unavailable: list[str] = []

    if not audio_bytes:
        return {
            "provider_name": "hume",
            "model": _HUME_MODEL,
            "provider_version": "hume-batch-v0",
            "processing_version": "s6_hume",
            "expression_observations": [],
            "signal_observations": [],
            "turn_segments": [],
            "evidence_coverage": 0.0,
            "evidence_reliability": 0.0,
            "unavailable_evidence": ["audio_missing"],
            "processing_warnings": ["audio_missing"],
        }

    derived = derive_acoustic_prosody(audio_bytes)
    unavailable.extend(list(derived.get("unavailable_evidence") or []))
    warnings.extend(list(derived.get("processing_warnings") or []))
    signals = list(derived.get("signal_observations") or [])

    try:
        payload = _submit_and_fetch_sync(audio_bytes, timeout_s=timeout, poll_s=poll)
    except PermissionError:
        raise
    except TimeoutError:
        raise
    except RuntimeError as exc:
        low = str(exc).lower()
        if "rate limited" in low or "discontinued" in low:
            raise
        raise RuntimeError(f"Hume prosody analysis failed: {exc}") from exc

    expressions, turn_segments = _parse_hume_predictions(payload)
    if not expressions:
        unavailable.append("hume_expression_empty")
        warnings.append("hume_expression_empty")

    confidences = [float(e.get("confidence") or 0.0) for e in expressions]
    reliability = sum(confidences) / len(confidences) if confidences else 0.0
    coverage = 1.0 if expressions else (0.5 if signals else 0.0)

    return {
        "provider_name": "hume",
        "model": _HUME_MODEL,
        "provider_version": "hume-batch-v0",
        "processing_version": "s6_hume",
        "expression_observations": expressions,
        "signal_observations": signals,
        "turn_segments": turn_segments,
        "evidence_coverage": round(coverage, 4),
        "evidence_reliability": round(reliability, 4),
        "unavailable_evidence": unavailable,
        "processing_warnings": warnings,
        "hume_job_payload_size": len(json.dumps(payload)) if payload else 0,
    }


class HumeProsodyProvider(AcousticFeatureProvider):
    """Production prosody via Hume Batch Expression Measurement (prosody model)."""

    def capabilities(self) -> AcousticFeatureCapabilities:
        return AcousticFeatureCapabilities(
            supports_pitch=True,
            supports_energy=True,
            supports_rhythm=True,
            supports_stress=False,
            provider_name="hume",
        )

    async def extract(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
    ) -> dict[str, object]:
        timeout = max(1, int(settings.SPEAKING_PROSODY_TIMEOUT_SECONDS or 120))
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_analyze_sync, audio_bytes),
                timeout=timeout + 15,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError("Hume prosody analysis timed out") from exc
