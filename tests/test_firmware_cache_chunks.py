"""Regression checks for ESPHome's 254-byte restored-string limit."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = (
    ROOT / "esphome" / "ha-menu-c3.yaml",
    ROOT / "esphome" / "packages" / "ha-menu-c3.yaml",
)
CHUNKS = 16
BLOCK_SIZE = 240
CACHE_LIMIT = 3800


def checksum(data: bytes) -> int:
    result = 2166136261
    for byte in data:
        result = ((result ^ byte) * 16777619) & 0xFFFFFFFF
    return result


def pack(data: bytes) -> list[bytes]:
    return [data[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE] for i in range(CHUNKS)]


class OfflineCacheStorageTests(unittest.TestCase):
    def test_all_restored_strings_obey_esphome_limit(self):
        for path in FIRMWARE:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                lengths = [
                    int(value)
                    for value in re.findall(r"max_restore_data_length:\s*(\d+)", source)
                ]
                self.assertEqual(lengths, [BLOCK_SIZE] * CHUNKS)
                for index in range(CHUNKS):
                    name = f"cached_menu_chunk_{index:02d}"
                    self.assertIn(f"- id: {name}", source)
                    self.assertEqual(source.count(f"&id({name})"), 2)
                self.assertTrue(all(0 < value <= 254 for value in lengths))
                self.assertNotIn("cached_menu_blob", source)
                self.assertIn("  - id: cached_menu_checksum", source)
                self.assertIn("crc == id(cached_menu_checksum)", source)
                self.assertIn("id(cached_menu_checksum) = checksum;", source)
                self.assertIn("cached.size() <= 3800U", source)
                self.assertIn('save_snapshot("");', source)
                self.assertIn('fw_version: "0.6.3"', source)

    def test_snapshot_round_trip_at_block_boundaries(self):
        for size in (0, 1, 239, 240, 241, 479, 480, 481, 3799, 3800):
            with self.subTest(length=size):
                # Unicode is stored as UTF-8 bytes, even across block boundaries.
                source = ("é".encode("utf-8") * 2000)[:size]
                chunks = pack(source)
                self.assertEqual(len(chunks), CHUNKS)
                self.assertTrue(all(len(part) <= BLOCK_SIZE for part in chunks))
                result = b"".join(chunks)
                self.assertEqual(result, source)
                self.assertEqual(checksum(result), checksum(source))

    def test_corruption_is_rejected(self):
        original = b"HA6" + b"-" * 3500
        chunks = pack(original)
        expected = checksum(original)
        chunks[8] = chunks[8].replace(b"-", b"x", 1)
        self.assertNotEqual(checksum(b"".join(chunks)), expected)
        self.assertGreater(len(original), 254)
        self.assertLessEqual(len(original), CACHE_LIMIT)

    def test_local_secrets_are_preserved(self):
        standalone = FIRMWARE[0].read_text(encoding="utf-8")
        package = FIRMWARE[1].read_text(encoding="utf-8")
        self.assertIn("key: !secret api_encryption_key", standalone)
        self.assertIn("password: !secret ota_password", standalone)
        self.assertNotIn("!secret", package)


if __name__ == "__main__":
    unittest.main()
