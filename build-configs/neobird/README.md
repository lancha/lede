# Neobird compatibility for the pinned LuCI feed

The theme source remains pinned to `thinktip/luci-theme-neobird@22ebcf0d09c4ec50594b11c1b5419d474970aaa2`.
After feeds are installed, `python3 scripts/neobird-compat.py apply .` ports the
theme using the Material templates and menu from the pinned LuCI feed. Their
SHA-256 values are checked before modification; changing the feed requires a
review of this port.

The original theme uses legacy Lua dispatcher menu functions. The port installs
ucode header/footer templates and a native `ui.menu` module, retaining the
password and recovery-mode warnings. The mobile breakpoint is 992px, matching
Neobird; the menu supports expanding/collapsing and viewport changes. The obsolete
header/footer are removed only from the freshly fetched build package.

`LUCI_MINIFY_CSS:=0` applies only to this theme. The current CSSTidy build path
changes declarations such as `--textColor` into `--textcolor` while retaining
`var(--textColor)`. That breaks text, menu, input, border, and background colors,
especially with the dark color scheme. The original CSS also contains distinct
font-face blocks that must be preserved.

CI runs the source regression tests before compilation. Before uploading any
firmware, it additionally opens the **built IPK** and checks CSS references,
ucode templates, and the menu module. The compatibility package is included
alongside the firmware artifacts and in `SHA256SUMS`; a source-only pass is not
accepted as evidence of correct packaged CSS.

```sh
python3 scripts/neobird-compat.py apply .
python3 -m unittest discover -s tests/neobird -p 'test_*.py' -v
node tests/neobird/menu.test.cjs
python3 scripts/neobird-compat.py verify-ipk /path/to/luci-theme-neobird.ipk
```

Build gates do not replace visual acceptance on the router: check login,
overview, iStore, OpenClash, and mobile navigation in light and dark modes.
No router configuration, password, subscription, or service is changed by this
build-time patch. Firmware installation remains a separate operation.
