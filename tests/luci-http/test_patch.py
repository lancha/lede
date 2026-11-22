import hashlib
import importlib.util
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("limit_patch", ROOT / "scripts/luci-multipart-limit.py")
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class PatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = Path(os.environ["LUCI_HTTP_FIXTURE"]).read_bytes()
        assert hashlib.sha256(cls.original).hexdigest() == patch.UPSTREAM_SHA256

    def test_apply_is_repeatable_and_only_multipart_changes(self):
        changed = patch.patched(self.original)
        self.assertEqual(changed, patch.patched(changed))
        self.assertEqual(changed.count(b"}, HTTP_MAX_CONTENT);"), 1)
        self.assertEqual(changed.count(b"}, HTTP_MAX_MULTIPART_CONTENT);"), 1)
        patch.verify(changed)
        with self.assertRaises(ValueError):
            patch.verify(self.original)

    def test_unknown_original_or_modified_patch_is_rejected(self):
        for data in [self.original + b"\n", patch.patched(self.original) + b"\n",
                     patch.patched(self.original).replace(b"1024*1024", b"1024*8192")]:
            with self.assertRaises(ValueError):
                patch.patched(data)

    def test_real_package_path_checked_without_extraction(self):
        def archive(name, data):
            out = io.BytesIO()
            with tarfile.open(fileobj=out, mode="w:gz") as tar:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            return out.getvalue()

        with tempfile.TemporaryDirectory() as tmp:
            ipk = Path(tmp) / "luci-base.ipk"
            for data, accepted in [(patch.patched(self.original), True), (self.original, False)]:
                payload = archive("./usr/share/ucode/luci/http.uc", data)
                ipk.write_bytes(archive("./data.tar.gz", payload))
                if accepted:
                    patch.verify_ipk(ipk)
                else:
                    with self.assertRaises(ValueError):
                        patch.verify_ipk(ipk)


if __name__ == "__main__":
    unittest.main()
