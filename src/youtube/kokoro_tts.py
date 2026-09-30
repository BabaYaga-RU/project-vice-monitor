"""Local Kokoro narration with an offline eSpeak NG emergency fallback."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

VOICE = os.environ.get("KOKORO_VOICE", "am_michael")
SAMPLE_RATE = 24_000


class LocalNarrator:
    """Load Kokoro once, synthesize local WAVs, and fall back as one batch."""

    def __init__(self, metadata_path: str | Path):
        self.metadata_path = Path(metadata_path)
        self.voice = VOICE
        self.engine = "kokoro-82m"
        self.pipeline = None
        self.model_load_seconds = 0.0
        self.synthesis_seconds = 0.0
        self.fallback_reason = ""

        started = time.perf_counter()
        try:
            from kokoro import KPipeline

            self.pipeline = KPipeline(lang_code="a")
        except Exception as error:  # noqa: BLE001 - use offline fallback if model setup fails
            self._use_espeak(error)
        finally:
            self.model_load_seconds = time.perf_counter() - started

    def _use_espeak(self, error: Exception) -> None:
        self.pipeline = None
        self.engine = "espeak-ng-fallback"
        self.fallback_reason = type(error).__name__
        if not (shutil.which("espeak-ng") or shutil.which("espeak")):
            raise RuntimeError("Kokoro failed and the local eSpeak NG fallback is unavailable.") from error

    def synthesize(self, texts: list[str], paths: list[Path], speed: float) -> dict:
        if len(texts) != len(paths) or not texts:
            raise ValueError("TTS requires matching nonempty text and WAV path lists.")
        started = time.perf_counter()
        if self.pipeline is not None:
            try:
                self._synthesize_kokoro(texts, paths, speed)
            except Exception as error:  # noqa: BLE001 - retry this complete batch offline
                self._use_espeak(error)
                self._synthesize_espeak(texts, paths, speed)
        else:
            self._synthesize_espeak(texts, paths, speed)
        self.synthesis_seconds += time.perf_counter() - started
        metadata = {
            "engine": self.engine,
            "voice": self.voice if self.engine == "kokoro-82m" else "en-us",
            "speed": round(speed, 3),
            "modelLoadSeconds": round(self.model_load_seconds, 3),
            "synthesisSeconds": round(self.synthesis_seconds, 3),
            "fallbackReason": self.fallback_reason,
        }
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        return metadata

    def _synthesize_kokoro(self, texts: list[str], paths: list[Path], speed: float) -> None:
        import numpy as np
        import soundfile as sf

        for text, path in zip(texts, paths):
            pieces = []
            for result in self.pipeline(text, voice=self.voice, speed=speed, split_pattern=r"\n+"):
                if result.audio is None:
                    continue
                audio = result.audio.detach().cpu().numpy() if hasattr(result.audio, "detach") else np.asarray(result.audio)
                audio = np.asarray(audio, dtype=np.float32).reshape(-1)
                if audio.size:
                    pieces.append(audio)
            if not pieces:
                raise RuntimeError("Kokoro returned no audio for a narration segment.")
            path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(path), np.concatenate(pieces), SAMPLE_RATE, subtype="PCM_16", format="WAV")

    @staticmethod
    def _synthesize_espeak(texts: list[str], paths: list[Path], speed: float) -> None:
        binary = shutil.which("espeak-ng") or shutil.which("espeak")
        if not binary:
            raise RuntimeError("The local eSpeak NG fallback is unavailable.")
        rate = max(150, min(190, round(175 * speed)))
        for text, path in zip(texts, paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [binary, "-v", "en-us", "-s", str(rate), "-w", str(path), text],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
