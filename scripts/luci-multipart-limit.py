#!/usr/bin/env python3
"""Bounded multipart fix for the pinned LuCI feed; reject unknown upstream files."""
import argparse
import hashlib
import io
import subprocess
import tarfile
from pathlib import Path

UPSTREAM_SHA256 = "68f8a7dffc7bccdfe98956cb3b6e0e087592c86049a2b83d061e5be3585fa5fa"
OLD_DECLARATION = "export let HTTP_MAX_CONTENT = 1024*100;\t\t// 100 kB maximum content size"
NEW_DECLARATION = OLD_DECLARATION + """

// OpenClash editors submit YAML as ordinary multipart fields, not file uploads.
// Bound each buffered multipart value/header at 1 MiB; retain the 100 KiB
// limits for URL-encoded and raw bodies, and keep file uploads streaming.
export let HTTP_MAX_MULTIPART_CONTENT = 1024*1024;"""
PARSER_LIMIT = "\t}, HTTP_MAX_CONTENT);"
NEW_PARSER_LIMIT = "\t}, HTTP_MAX_MULTIPART_CONTENT);"


def original_or_fail(data):
    text = data.decode()
    if NEW_DECLARATION in text and NEW_PARSER_LIMIT in text:
        text = text.replace(NEW_DECLARATION, OLD_DECLARATION, 1)
        text = text.replace(NEW_PARSER_LIMIT, PARSER_LIMIT, 1)
    if hashlib.sha256(text.encode()).hexdigest() != UPSTREAM_SHA256:
        raise ValueError("Unknown LuCI http.uc; review upstream before applying this patch")
    return text


def patched(data):
    text = original_or_fail(data)
    return text.replace(OLD_DECLARATION, NEW_DECLARATION, 1).replace(
        PARSER_LIMIT, NEW_PARSER_LIMIT, 1
    ).encode()


def verify(data):
    if data != patched(data):
        raise ValueError("LuCI multipart fix is missing")


def verify_ipk(path):
    # Inspect both supported IPK envelopes without unpacking into the filesystem.
    if path.read_bytes()[:8] == b"!<arch>\n":
        names = subprocess.check_output(["ar", "t", str(path)], text=True).splitlines()
        names = [name for name in names if name.startswith("data.tar")]
        if len(names) != 1:
            raise ValueError("Expected one data archive")
        payload = subprocess.check_output(["ar", "p", str(path), names[0]])
    else:
        with tarfile.open(path, "r:*") as archive:
            members = [m for m in archive.getmembers()
                       if m.name.removeprefix("./").startswith("data.tar") and m.isfile()]
            if len(members) != 1:
                raise ValueError("Expected one data archive")
            payload = archive.extractfile(members[0]).read()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
        members = [m for m in archive.getmembers()
                   if m.name.removeprefix("./") == "usr/share/ucode/luci/http.uc" and m.isfile()]
        if len(members) != 1:
            raise ValueError("Expected one installed LuCI HTTP module")
        verify(archive.extractfile(members[0]).read())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["apply", "verify", "verify-ipk"])
    parser.add_argument("path", type=Path, help="http.uc source file, or luci-base IPK")
    args = parser.parse_args()
    if args.mode == "apply":
        data = args.path.read_bytes()
        result = patched(data)
        if result != data:
            args.path.write_bytes(result)
        verify(args.path.read_bytes())
    elif args.mode == "verify":
        verify(args.path.read_bytes())
    else:
        verify_ipk(args.path)
    print(f"LuCI multipart {args.mode}: PASS")


if __name__ == "__main__":
    main()
