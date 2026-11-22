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

The ESXi ARM64 workflow on `codex/esxi-arm64-features` applies this port before
firmware compilation. Build 11 at `8506dc50fa86b952f629a6a00fcd1eb84de606d3`
completed the port, configuration, firmware, packaged-IPK verification, and
artifact upload steps successfully. Its artifact includes the theme IPK,
firmware, resolved configuration, manifest, build provenance, and checksums.
This is a build result, not a claim that the resulting firmware was installed
or visually verified on the router. The fix is on the feature branch; it is
not present in `master` unless separately merged.

Build gates do not replace visual acceptance on the router: check login,
overview, iStore, OpenClash, and mobile navigation in light and dark modes.
No router configuration, password, subscription, or service is changed by this
build-time patch. Firmware installation remains a separate operation.

## Layout completion (2026-11-22)

Layout reference: `0x676e67/luci-theme-design@5cea733806ccaf17fd63790d171bb2b65f29f8bd`
(Apache-2.0), particularly `dev/style.css` and the header layout. Design itself
derives from Neobird. This port borrows the sidebar, card, form, responsive table,
and bottom-navigation layout concepts; it does not import the Design palette,
fonts, JavaScript runtime, or legacy Lua templates.

The original Neobird CSS remains byte-for-byte unchanged. The compatibility layer
can define only `--nb-*` layout variables, and colors must reference existing
Neobird variables. Source and built-IPK checks enforce this. In particular the
original dark-mode badge color is deliberately preserved.

Modern `div.cbi-section` cards now receive the legacy card treatment. The header
and independently scrolling sidebar reserve room for the fixed bottom bar, while
footer and page actions stay in document flow. The generated ucode footer closes
both the container and main content before rendering version information.
Protected URLs receive the centered login layout whenever unauthenticated.

`menu-layout.js` fills the five bottom slots only from the ACL-filtered menu tree
and prefers installed OpenClash over legacy proxy plugins. Missing routes are
omitted. Read-only wide tables receive their own scroll wrapper; interactive
tables use labelled stacked cells on phones so dropdowns are not clipped by an
overflow container. Native dropdown, tab and modal geometry is also supplied.

The `layout` Actions job is required before firmware compilation. It applies the
port to hash-checked fixtures, runs source/menu checks, then renders a **synthetic
modern LuCI fixture** in Chromium at 1440, 1024, 390 and 320 pixels in both color
schemes. Checks cover card colors, page overflow, authorized quick links, mobile
menu dismissal, dropdown/modal geometry, unobscured actions and login. Screenshots
and machine-readable results are uploaded even on failure; firmware compilation
is blocked by a failed layout job.

For manual local review after `apply`, run
`python3 tests/neobird/serve-preview.py` and open
`http://127.0.0.1:8876/tests/neobird/preview-sizes.html`.
Preview files and browser dependencies are test fixtures, not installed packages.
These checks do not exercise live ubus/RPC, OpenClash/iStore internals, browser
extensions, real phone safe areas, or router upgrades. A persistent "Collecting
data..." state requires separate runtime diagnosis; no CSS success implies that
data loading has been repaired.
