import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.youtube.shorts import _article_script, create_short


class SharedShortRendererTests(unittest.TestCase):
    def test_script_uses_article_content_and_short_cta(self):
        article = {
            "title": "Rockstar confirms a new GTA six update today",
            "description": "Rockstar confirmed a new trailer date for Grand Theft Auto six. The studio shared the announcement on its official newsroom.",
            "sections": [{"heading": "The announcement", "paragraphs": ["The trailer will arrive on the date stated in the company's official announcement."]}],
            "articleUrl": "https://example.test/blog/article/",
        }
        beats = _article_script(article)
        self.assertTrue("GTA update" in " ".join(beat[1] for beat in beats[:2]))
        self.assertTrue(beats[-1][1].endswith("Blog."))
        self.assertTrue(all(len(narration.split()) <= 6 for _, narration in beats))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe required")
    def test_renders_vertical_h264_with_audio_and_burned_captions(self):
        article = {
            "title": "Rockstar confirms a new Grand Theft Auto six trailer date today",
            "description": "Rockstar Games confirmed the next trailer date for Grand Theft Auto six. The studio published the announcement through its official newsroom today.",
            "sections": [{"heading": "Official announcement", "paragraphs": ["The published statement also confirmed that the trailer will arrive on the date the studio announced."]}],
            "articleUrl": "https://example.test/blog/test-story/",
            "thumbnail": "",
            "inlineImages": [],
        }
        with tempfile.TemporaryDirectory(prefix="macca-short-test-") as temp:
            output = Path(temp) / "test.mp4"
            if os.name == "nt":
                tts_command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File {Path(__file__).with_name("windows_sapi_tts.ps1")}'
            else:
                tts_command = f'"{os.sys.executable}" "{Path(__file__).with_name("fake_tts.py")}"'
            with patch.dict(os.environ, {"SHORTS_TTS_COMMAND": tts_command, "SHORTS_MUSIC_PATH": "", "SHORTS_RENDERER": "narrated"}):
                video = create_short(article, output, Path(temp) / "work")
            probe = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)
            ], text=True))
            stream = next(item for item in probe["streams"] if item["codec_type"] == "video")
            audio = next(item for item in probe["streams"] if item["codec_type"] == "audio")
            duration = float(probe["format"]["duration"])
            self.assertEqual("h264", stream["codec_name"])
            self.assertEqual(1080, stream["width"])
            self.assertEqual(1920, stream["height"])
            self.assertEqual("30/1", stream["r_frame_rate"])
            self.assertEqual("aac", audio["codec_name"])
            self.assertGreaterEqual(duration, 15)
            self.assertLessEqual(duration, 25)
            self.assertGreater(output.stat().st_size, 50000)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe required")
    def test_legacy_slideshow_remains_available_for_rollback(self):
        article = {"title": "Legacy renderer rollback test", "description": "The old renderer stays available.", "sections": []}
        with tempfile.TemporaryDirectory(prefix="macca-legacy-test-") as temp:
            output = Path(temp) / "legacy.mp4"
            with patch.dict(os.environ, {"SHORTS_RENDERER": "legacy"}):
                video = create_short(article, output, Path(temp) / "work")
            probe = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)
            ], text=True))
            stream = next(item for item in probe["streams"] if item["codec_type"] == "video")
            self.assertEqual("h264", stream["codec_name"])
            self.assertEqual(1080, stream["width"])
            self.assertEqual(1920, stream["height"])


if __name__ == "__main__":
    unittest.main()
