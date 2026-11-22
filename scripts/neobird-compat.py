#!/usr/bin/env python3
"""Apply the Neobird port to the pinned LuCI feed; verify source or packaged files."""
import argparse
import hashlib
import io
import re
import subprocess
import tarfile
from pathlib import Path

MATERIAL_HASHES = {
    "ucode/template/themes/material/header.ut":
        "1650823a3ee8218525b7de4a01fe28eb1e4b34d8b7691c78f8de49c806a7babe",
    "ucode/template/themes/material/footer.ut":
        "11645e45340e970b78039dcd242b0381d7e34c3604f4a1e4db9201621952ef2b",
    "htdocs/luci-static/resources/menu-material.js":
        "e2623d099454b2c1a24514b029dad73192eea0aeff8bee493c1b5d383d6a274c",
}
STYLE_HASH = "8441b5dc530930f926af607d8d9e5174b8062c6407beb6d4a92deefcb696fe49"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Unexpected upstream content: {old!r}")
    return text.replace(old, new, 1)


def check_css(text):
    # CSS custom properties are case-sensitive. CSSTidy lowercases their
    # declarations but preserves var() references, breaking this theme.
    definitions = set(re.findall(r"(--[\w-]+)\s*:", text))
    references = set(re.findall(r"var\(\s*(--[\w-]+)", text))
    missing = sorted(references - definitions)
    if missing:
        raise ValueError(f"Undefined CSS custom properties: {', '.join(missing)}")
    if "--textColor" not in definitions or "--mainleftbgColor" not in definitions:
        raise ValueError("Neobird color definitions missing")


def apply(root):
    theme = root / "package/luci-theme-neobird"
    material = root / "feeds/luci/themes/luci-theme-material"
    source = {}
    for name, expected in MATERIAL_HASHES.items():
        data = (material / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"LuCI changed; review the Neobird port before building: {name}")
        source[name] = data.decode()

    makefile = theme / "Makefile"
    text = makefile.read_text()
    if "LUCI_MINIFY_CSS:=0" not in text:
        text = replace_once(text, "LUCI_DEPENDS:=", "LUCI_MINIFY_CSS:=0\nLUCI_DEPENDS:=+luci-base")
    text = re.sub(r"^PKG_RELEASE:=\d+$", "PKG_RELEASE:=2026112201", text, flags=re.M)
    makefile.write_text(text)

    header = source["ucode/template/themes/material/header.ut"]
    header = replace_once(
        header, '<link rel="stylesheet" href="{{ media }}/cascade.css">',
        '<link rel="stylesheet" href="{{ media }}/css/style.css">\n'
        '<link rel="stylesheet" href="{{ media }}/css/luci-compat.css">\n'
        '<meta name="darkreader-lock">')
    header = replace_once(header, "{{ media }}/logo_48.png", "{{ media }}/images/icon.png")
    header = replace_once(header, "{{ media }}/logo.svg", "{{ media }}/favicon.ico")
    header = replace_once(header, '<span class="showSide"></span>',
                          '<button type="button" class="showSide" aria-label="{{ _(\'Menu\') }}" '
                          'aria-controls="mainmenu" aria-expanded="false">☰</button>')
    header = replace_once(header, "{{ media }}/brand.png", "{{ media }}/images/logo.png")
    header = replace_once(header, 'alt="OpenWrt"', 'alt="Neobird"')
    header = replace_once(header, 'content="width=device-width, initial-scale=1"',
                          'content="width=device-width, initial-scale=1, viewport-fit=cover"')
    header = replace_once(header,
        '\t\t\t<a class="brand" href="#">{{ striptags(`${boardinfo.hostname ?? \'?\'}`) }}</a>\n', "")
    header = replace_once(header, '<span class="status" id="indicators">',
                          '<span class="pull-right" id="indicators">')
    # Neobird's historical page selectors omit the admin category.
    header = replace_once(header, "`node-${join('-', ctx.path)}`",
                          "`node-${join('-', slice(ctx.path, 1))}`")
    # Auth forms may be served at /admin/network/...: path length alone is not
    # a login detector. Keep the centered login layout on all protected routes.
    header = replace_once(header, "length(ctx.path) ? `node-",
                          "ctx.authsession && length(ctx.path) ? `node-")
    header = replace_once(header, '<div class="main">',
                          '{% if (ctx.authsession): %}\n'
                          '<nav class="navbar" id="neobird-quicklinks" '
                          'aria-label="{{ _(\'Navigation\') }}" hidden></nav>\n'
                          '{% endif %}\n<div class="main">')
    footer = source["ucode/template/themes/material/footer.ut"].replace("menu-material", "menu-neobird")
    footer = replace_once(footer, "<script>L.require('menu-neobird')</script>",
                          "{% if (ctx.authsession): %}\n"
                          "\t<script>L.require('menu-neobird')</script>\n\t{% endif %}")
    # Close both .container and #maincontent before the footer; the two
    # remaining closes belong to .main-right and .main.
    footer = replace_once(footer, '\t\t\t</div>\n\t\t\t<footer',
                          '\t\t\t</div>\n\t\t</div>\n\t\t<footer')

    menu = source["htdocs/luci-static/resources/menu-material.js"]
    menu = replace_once(menu, "\trender(tree) {",
                         (root / "build-configs/neobird/menu-layout.js").read_text()
                         + "\trender(tree) {\n"
                         "\t\tthis.renderQuickLinks(tree);\n\t\tthis.setupTableLayout();")
    menu = menu.replace("1152", "992")
    menu = replace_once(menu, "node = node.children[L.env.dispatchpath[i]];",
                         "node = node.children && node.children[L.env.dispatchpath[i]];")
    menu = replace_once(menu, "'data-title': hasChildren ? '' : _(child.title),", "'data-title': child.title,")
    menu = replace_once(menu, "const a = ev.target;", "const a = ev.currentTarget;")
    menu = replace_once(menu, "const ul2 = a.nextElementSibling;",
                         "const ul2 = a.nextElementSibling;\n"
                         "\t\tconst wasOpen = ul1.classList.contains('active');")
    menu = replace_once(menu, "if (!ul2)\n\t\t\treturn;",
                         "if (!ul2 || wasOpen) {\n"
                         "\t\t\tev.preventDefault();\n\t\t\tev.stopPropagation();\n\t\t\treturn;\n\t\t}")
    # Keep ARIA synchronized on click, overlay dismissal, and viewport resize.
    menu = replace_once(menu, "mainLeft.style.visibility = open ? '' : 'visible';",
                         "mainLeft.style.visibility = open ? '' : 'visible';\n"
                         "\t\tdocument.querySelector('.showSide')"
                         ".setAttribute('aria-expanded', String(!open));")

    outputs = {
        "ucode/template/themes/neobird/header.ut": header,
        "ucode/template/themes/neobird/footer.ut": footer,
        "htdocs/luci-static/resources/menu-neobird.js": menu,
        "htdocs/luci-static/neobird/css/luci-compat.css":
            (root / "build-configs/neobird/luci-compat.css").read_text(),
    }
    for name, text in outputs.items():
        path = theme / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    # Only obsolete templates inside the freshly fetched package are removed.
    # The legacy dispatcher calls cannot run on this pinned ucode LuCI.
    for name in ("header.htm", "footer.htm"):
        (theme / "luasrc/view/themes/neobird" / name).unlink(missing_ok=True)
    verify_source(root)


def verify(read):
    style = read("www/luci-static/neobird/css/style.css")
    compat = read("www/luci-static/neobird/css/luci-compat.css")
    check_css(style + "\n" + compat)
    if hashlib.sha256(style.encode()).hexdigest() != STYLE_HASH:
        raise ValueError("Packaged Neobird CSS differs from the reviewed, unminified source")
    if ".slide.active > .slide-menu" not in compat or "@media (max-width: 992px)" not in compat:
        raise ValueError("Responsive menu compatibility rules missing")
    if "#maincontent .cbi-section" not in compat or "#neobird-quicklinks" not in compat:
        raise ValueError("Modern section or quick navigation layout missing")
    # Palette changes must never hide inside the layout compatibility layer.
    if re.search(r"#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\s*\(", compat):
        raise ValueError("Layout layer must reuse Neobird colors, not add literals")
    if re.search(r"--(?!nb-)[\w-]+\s*:", compat):
        raise ValueError("Layout layer must not override Neobird palette variables")
    header = read("usr/share/ucode/luci/template/themes/neobird/header.ut")
    footer = read("usr/share/ucode/luci/template/themes/neobird/footer.ut")
    if "/css/style.css" not in header or "/css/luci-compat.css" not in header:
        raise ValueError("Neobird styles are not loaded by the ucode header")
    if "neobird-quicklinks" not in header or "ctx.authsession && length(ctx.path)" not in header:
        raise ValueError("Native quick navigation or protected-route login layout missing")
    if "ctx.authsession" not in footer or "menu-neobird" not in footer:
        raise ValueError("Authenticated native LuCI menu loader missing")
    menu = read("www/luci-static/resources/menu-neobird.js")
    if "ui.menu.load()" not in menu or "992" not in menu or "renderQuickLinks" not in menu:
        raise ValueError("Native LuCI menu module missing")


def verify_source(root):
    theme = root / "package/luci-theme-neobird"
    def read(name):
        name = name.replace("www/", "htdocs/", 1).replace("usr/share/ucode/luci/", "ucode/", 1)
        return (theme / name).read_text()
    verify(read)
    if "LUCI_MINIFY_CSS:=0" not in (theme / "Makefile").read_text():
        raise ValueError("CSS minification must be disabled for Neobird")


def verify_ipk(path):
    # OpenWrt packages may use a tar or ar outer container. Read members only;
    # never extract package files to the build machine's filesystem.
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            entries = [m for m in archive.getmembers() if Path(m.name).name.startswith("data.tar")]
            if len(entries) != 1:
                raise ValueError("Expected one data archive in IPK")
            payload = archive.extractfile(entries[0]).read()
    else:
        names = subprocess.check_output(["ar", "t", str(path)], text=True).splitlines()
        names = [name for name in names if name.startswith("data.tar")]
        if len(names) != 1:
            raise ValueError("Expected one data archive in IPK")
        payload = subprocess.check_output(["ar", "p", str(path), names[0]])
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
        members = {m.name.removeprefix("./"): m for m in archive.getmembers() if m.isfile()}
        verify(lambda name: archive.extractfile(members[name]).read().decode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["apply", "verify-source", "verify-ipk"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    {"apply": apply, "verify-source": verify_source, "verify-ipk": verify_ipk}[args.mode](args.path)
    print(f"Neobird {args.mode}: PASS")
