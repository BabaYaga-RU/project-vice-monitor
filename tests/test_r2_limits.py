import unittest
from datetime import datetime, timedelta, timezone

from src.youtube.r2_limits import MAX_OBJECT_BYTES, reserve_r2_upload


class R2LimitsTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        self.state = {
            "schemaVersion": 1,
            "month": "2026-09",
            "monthlyUploadAttempts": 0,
            "recentUploadAttempts24h": [],
            "articles": {},
        }

    def reserve(self, slug="story", **kwargs):
        size_bytes = kwargs.pop("size_bytes", 1024)
        return reserve_r2_upload(
            self.state,
            slug=slug,
            object_key=f"instagram-reels/{slug}.mp4",
            size_bytes=size_bytes,
            now=self.now,
            **kwargs,
        )

    def test_rejects_over_25_mib_and_accepts_boundary(self):
        too_large = reserve_r2_upload(
            self.state,
            slug="large",
            object_key="large.mp4",
            size_bytes=MAX_OBJECT_BYTES + 1,
            now=self.now,
        )
        self.assertEqual(too_large[0], 0)
        self.assertEqual(self.state["monthlyUploadAttempts"], 0)
        self.assertEqual(self.reserve(slug="boundary", size_bytes=MAX_OBJECT_BYTES), (2, ""))

    def test_only_one_reservation_per_article(self):
        self.assertEqual(self.reserve()[0], 2)
        attempts, reason = self.reserve()
        self.assertEqual(attempts, 0)
        self.assertIn("already", reason)
        self.assertEqual(self.state["monthlyUploadAttempts"], 2)

    def test_only_one_object_per_run(self):
        attempts, reason = self.reserve(objects_reserved_this_run=1)
        self.assertEqual(attempts, 0)
        self.assertIn("Per-run", reason)

    def test_rolling_24_hour_quota_counts_each_attempt(self):
        timestamp = (self.now - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        self.state["recentUploadAttempts24h"] = [timestamp] * 23
        attempts, _ = self.reserve()
        self.assertEqual(attempts, 1)
        self.assertEqual(len(self.state["recentUploadAttempts24h"]), 24)
        attempts, reason = self.reserve(slug="another", objects_reserved_this_run=0)
        self.assertEqual(attempts, 0)
        self.assertIn("limit", reason)

    def test_monthly_limit_and_month_rollover(self):
        self.state["monthlyUploadAttempts"] = 749
        attempts, _ = self.reserve()
        self.assertEqual(attempts, 1)
        self.assertEqual(self.state["monthlyUploadAttempts"], 750)

        next_month = self.now + timedelta(days=1)
        old_recent = (next_month - timedelta(days=1, seconds=1)).isoformat().replace("+00:00", "Z")
        self.state["recentUploadAttempts24h"] = [old_recent]
        attempts, _ = reserve_r2_upload(
            self.state,
            slug="october",
            object_key="october.mp4",
            size_bytes=1024,
            now=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
        )
        self.assertEqual(attempts, 2)
        self.assertEqual(self.state["month"], "2026-10")
        self.assertEqual(self.state["monthlyUploadAttempts"], 2)
        self.assertEqual(len(self.state["recentUploadAttempts24h"]), 2)


if __name__ == "__main__":
    unittest.main()
