import importlib.util
import io
import re
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("compat", ROOT / "scripts/neobird-compat.py")
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)
THEME = ROOT / "package/luci-theme-neobird"


class NeobirdRegression(unittest.TestCase):
    def test_original_variable_names_resolve(self):
        compat.verify_source(ROOT)

    def test_csstidy_lowercase_regression_is_rejected(self):
        css = (THEME / "htdocs/luci-static/neobird/css/style.css").read_text()
        broken = re.sub(r"(--[\w-]+)(\s*:)", lambda m: m[1].lower() + m[2], css)
        with self.assertRaisesRegex(ValueError, "Undefined CSS custom properties"):
            compat.check_css(broken)

    def test_upstream_template_drift_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Unexpected upstream"):
            compat.replace_once("renamed upstream", "expected template", "replacement")

    def test_generated_templates_use_native_dispatcher(self):
        header = (THEME / "ucode/template/themes/neobird/header.ut").read_text()
        footer = (THEME / "ucode/template/themes/neobird/footer.ut").read_text()
        self.assertIn("slice(ctx.path, 1)", header)
        self.assertIn("getspnam('root')", header)
        self.assertIn("rootfs_type", header)
        self.assertIn("ctx.authsession && length(ctx.path)", header)
        self.assertIn('id="neobird-quicklinks"', header)
        self.assertIn("viewport-fit=cover", header)
        self.assertIn("{% if (ctx.authsession): %}", footer)
        self.assertFalse((THEME / "luasrc/view/themes/neobird/header.htm").exists())
        self.assertFalse((THEME / "luasrc/view/themes/neobird/footer.htm").exists())

    def test_layout_keeps_original_palette_and_mobile_controls(self):
        css = (THEME / "htdocs/luci-static/neobird/css/luci-compat.css").read_text()
        # A copied Design palette must fail even if every variable resolves.
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\s*\(")
        self.assertNotRegex(css, r"--(?!nb-)[\w-]+\s*:")
        for contract in ("#maincontent .cbi-section", "div.table > .tr",
                         ".cbi-dropdown[open] > ul.dropdown",
                         "body.node-main-login", "env(safe-area-inset-bottom",
                         "#maincontent .label"):
            self.assertIn(contract, css)

    def test_packaged_files_checked_not_just_source(self):
        def tar_blob(files):
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
                for name, content in files.items():
                    info = tarfile.TarInfo("./" + name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            return buffer.getvalue()

        files = {}
        for source, dest in [("htdocs", "www"), ("ucode", "usr/share/ucode/luci")]:
            for path in (THEME / source).rglob("*"):
                if path.is_file():
                    files[f"{dest}/{path.relative_to(THEME / source)}"] = path.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            ipk = Path(directory) / "theme.ipk"
            ipk.write_bytes(tar_blob({"data.tar.gz": tar_blob(files)}))
            compat.verify_ipk(ipk)
            # A build that silently minifies the final CSS must fail publication.
            name = "www/luci-static/neobird/css/style.css"
            files[name] = files[name].replace(b"--textColor:", b"--textcolor:")
            ipk.write_bytes(tar_blob({"data.tar.gz": tar_blob(files)}))
            with self.assertRaisesRegex(ValueError, "Undefined CSS custom properties"):
                compat.verify_ipk(ipk)


if __name__ == "__main__":
    unittest.main()
