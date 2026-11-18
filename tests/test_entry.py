"""Gate checks for the news-image entry, standard library only.

Runs main.py twice into two temporary output directories and asserts:
both runs write byte-identical entry.png files (sha256), the PNG
signature is right, the IHDR dimensions are within 1024x1024, the file
is at most 1 MiB, and the IDAT stream zlib-decompresses to exactly the
scanlines the header describes.
"""

import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(REPO_ROOT, "main.py")
MAX_BYTES = 1048576
MAX_DIM = 1024


def run_once(out_dir):
    env = dict(os.environ)
    env["MAKEFUN_OUTPUT_DIR"] = out_dir
    proc = subprocess.run([sys.executable, MAIN], env=env,
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise AssertionError("main.py failed: " + proc.stderr)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "rb") as fh:
        return fh.read()


def parse_chunks(data):
    chunks = []
    pos = 8
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise AssertionError("bad CRC on chunk %r" % kind)
        chunks.append((kind, body))
        pos += 12 + length
    return chunks


class EntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d1, \
                tempfile.TemporaryDirectory() as d2:
            cls.first = run_once(d1)
            cls.second = run_once(d2)

    def test_two_runs_byte_identical(self):
        h1 = hashlib.sha256(self.first).hexdigest()
        h2 = hashlib.sha256(self.second).hexdigest()
        self.assertEqual(h1, h2)
        self.assertEqual(self.first, self.second)

    def test_png_signature(self):
        self.assertEqual(self.first[:8], b"\x89PNG\r\n\x1a\n")

    def test_dimensions_and_size_within_gate(self):
        width, height = struct.unpack(">II", self.first[16:24])
        self.assertLessEqual(width, MAX_DIM)
        self.assertLessEqual(height, MAX_DIM)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        self.assertLessEqual(len(self.first), MAX_BYTES)

    def test_idat_decompresses(self):
        chunks = parse_chunks(self.first)
        kinds = [k for k, _ in chunks]
        self.assertEqual(kinds[0], b"IHDR")
        self.assertEqual(kinds[-1], b"IEND")
        width, height = struct.unpack(">II", self.first[16:24])
        idat = b"".join(body for kind, body in chunks if kind == b"IDAT")
        raw = zlib.decompress(idat)
        self.assertEqual(len(raw), height * (1 + width * 3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
