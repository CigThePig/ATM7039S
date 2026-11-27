"""Regression tests for the recovery diagnostic; no physical card needed."""
import hashlib
from io import BytesIO
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import v3_rootfs_review as review


class Node:
    def __init__(self, inum, kind, data=b'', children=None, target=None):
        self.inum = inum
        self.inode = SimpleNamespace(i_mode=kind | 0o755, i_uid=0, i_gid=0,
                                     i_links_count=1, i_flags=0)
        self.data = data
        self.size = len(data)
        self.xattr = []
        self.children = children or {}
        self.link = target
        self.reads = 0

    def open(self):
        self.reads += 1
        return BytesIO(self.data)

    def listdir(self):
        return self.children


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.file = Node(3, stat.S_IFREG, b'original')
        self.other = Node(4, stat.S_IFREG, b'other')
        # LIFO traversal means 'file' is the first non-root node.
        self.root = Node(2, stat.S_IFDIR, children={'other': self.other, 'file': self.file})
        self.fs = SimpleNamespace(get=lambda path: self.root)
        self.digest = 'a' * 64

    def scan(self, path, **kwargs):
        return review.snapshot(self.fs, 'fixture', self.folder / path, self.digest, **kwargs)

    def test_interrupted_scan_recovers_without_rehashing_completed_files(self):
        with self.assertRaises(KeyboardInterrupt):
            self.scan('resume.sqlite', interrupt_after=2)
        self.assertEqual(self.file.reads, 1)
        resumed = self.scan('resume.sqlite')
        self.assertEqual(self.file.reads, 1)
        fresh = self.scan('fresh.sqlite')
        self.assertEqual(resumed, fresh)
        self.assertEqual(set(resumed), {'/', '/file', '/other'})
        self.assertEqual(resumed['/file']['sha256'], hashlib.sha256(b'original').hexdigest())

    def test_completed_checkpoint_reuse_and_identity(self):
        first = self.scan('done.sqlite')
        second = self.scan('done.sqlite')
        self.assertEqual(first, second)
        self.assertEqual(self.file.reads, 1)
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
            review.snapshot(self.fs, 'fixture', self.folder/'done.sqlite', 'b'*64)

    def test_modified_file_and_added_link_are_reported(self):
        a = self.scan('a.sqlite')
        self.file.data = b'changed'
        self.file.size = len(self.file.data)
        self.root.children['link'] = Node(5, stat.S_IFLNK, target='/var/run/dropbear')
        b = review.snapshot(self.fs, 'fixture', self.folder/'b.sqlite', 'b'*64)
        diff = review.compare(a,b)
        self.assertEqual(diff['added'], ['/link'])
        self.assertEqual(diff['removed'], [])
        self.assertEqual(diff['changed'][0]['path'], '/file')
        self.assertIn('sha256', diff['changed'][0]['fields'])

    def test_atomic_copy_rejects_wrong_hash(self):
        content = bytearray(4096)
        content[1080:1082] = b'\x53\xef'
        dest = self.folder/'snapshot'
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            review.copy_stream(BytesIO(content), dest, len(content), 'fixture', '0'*64)
        self.assertFalse(dest.exists())

    def test_missing_card_fails_before_scan(self):
        with self.assertRaisesRegex(RuntimeError, 'found 0'):
            review.detect_card(str(self.folder/'missing'), 4096)

    def test_atomic_report(self):
        out = self.folder/'report.json'
        review.atomic_json(out, {'done': True})
        self.assertIn('"done": true', out.read_text(encoding='utf-8'))
        self.assertFalse((self.folder/'report.json.tmp').exists())


if __name__ == '__main__':
    unittest.main()
