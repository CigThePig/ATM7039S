"""v3_rootfs_review.py 3.x against real (synthetic) ext4 fixtures; no physical card needed."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

try:
    import dissect.extfs  # noqa: F401
    import v3_rootfs_review as review
    import lab_fixture as lf
    from v3lab.steps import Env
    from v3lab.store import StoreError
    OK = True
except ImportError:
    OK = False


@unittest.skipUnless(OK, 'dissect.extfs not installed')
class ReviewTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)
        self.root = lf.make_root(self.tmp / 'root')
        self.data = self.tmp / 'data'
        (self.data / 'cache/firmware').mkdir(parents=True)
        (self.data / 'cache/firmware/koriki-v1.0-rootfs.ext4').write_bytes(lf.container('pristine'))
        self.world = lf.World(self.tmp)
        self.world.card.flash()
        self.env = Env(root=self.root, data=self.data, inventory=self.world.inventory)

    def tearDown(self):
        self._t.cleanup()

    def test_prepared_then_post_capture(self):
        self.world.card.first_boot()
        rep, out = review.review(self.env, 'prepared')
        self.assertEqual(rep['verdict'], 'PASS', rep['items'])
        self.world.card.capture_boot()
        rep2, _ = review.review(self.env, 'post-capture', baseline=out / 'card-prepared.json')
        self.assertEqual(rep2['verdict'], 'PASS', rep2['items'])

    def test_explicit_card_path_and_tamper(self):
        self.world.card.first_boot('tampered')
        rep, _ = review.review(self.env, 'prepared', card=str(self.world.card.boot / 'boot' / 'BATOCERA'))
        self.assertEqual(rep['verdict'], 'FAIL')

    def test_missing_card_is_a_plain_error(self):
        self.world.card.connected = False
        with self.assertRaisesRegex(StoreError, 'exactly one Koriki card'):
            review.review(self.env, 'prepared')
        with self.assertRaisesRegex(StoreError, 'does not exist'):
            review.review(self.env, 'prepared', card=str(self.tmp / 'nope'))

    def test_post_capture_requires_baseline(self):
        with self.assertRaisesRegex(StoreError, 'baseline'):
            review.review(self.env, 'post-capture')


if __name__ == '__main__':
    unittest.main()
