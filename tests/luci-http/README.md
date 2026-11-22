# LuCI multipart editor limit

The deployed router's `http.uc` and the pinned LuCI source have SHA-256
`68f8a7dffc7bccdfe98956cb3b6e0e087592c86049a2b83d061e5be3585fa5fa`.
Both pass 102,400 to `lucihttp.multipart_parser()`. Its C implementation caps
each buffered header/value, not the aggregate request. Ordinary textarea fields
are buffered; file fields use streaming callbacks or temporary files.

OpenClash's legacy configuration form includes editable and readonly `TextValue`
fields. A 200,555-byte configuration exceeds the old per-field limit, before
the form's save handler runs. This is independent of theme CSS.

`scripts/luci-multipart-limit.py` raises only the multipart parser buffer ceiling
to **1 MiB**. URL-encoded and raw bodies retain 100 KiB; Content-Length checking,
streaming file uploads, dispatcher authentication and CSRF checks are unchanged.
This is a per-field/header bound, not a new aggregate request limit. The change
applies to all LuCI multipart forms and allows higher bounded memory consumption.
It does not make arbitrarily large inline YAML editable.

The patch is guarded by the original full-file hash, is repeatable, and rejects
upstream changes for review. CI tests the real pinned ucode + lucihttp native
decoder before firmware compilation. The finished luci-base IPK is also checked
for the exact patched module, then included in the firmware artifact.

Run on Linux with cmake, gcc, git, curl, pkg-config and libjson-c-dev:

```sh
bash tests/luci-http/run.sh
```

Tests cover 100 KiB boundaries, the reported configuration size using **synthetic
data only**, exact 1 MiB and rejection above it, repeated fields, token preservation,
2 MiB streamed files, and unchanged raw/URL-encoded/Content-Length protections.
They do not submit real settings, call OpenClash handlers, restart proxies, or
prove authenticated browser saves succeeded on a running router.
