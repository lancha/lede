#!/usr/bin/env bash
# Build the pinned native parser in a disposable directory, without installing
# anything into system paths. Requires cmake, gcc, pkg-config and libjson-c-dev.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
work="$(mktemp -d "${RUNNER_TEMP:-/tmp}/luci-http-regression.XXXXXX")"
prefix="$work/runtime"

for spec in \
  jow-/ucode:b885dd0fe1e974551fb1233ca5f3aa74d80b74d9 \
  jow-/lucihttp:9b5b683fbb2bb0010aa031d620d0ab8105516757
do
  repo="${spec%:*}"
  sha="${spec##*:}"
  target="$work/${repo##*/}"
  git init -q "$target"
  git -C "$target" fetch --no-tags --depth=1 "https://github.com/$repo.git" "$sha"
  git -C "$target" checkout --detach FETCH_HEAD
done

cmake -S "$work/ucode" -B "$work/ucode-build" \
  -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_INSTALL_RPATH="$prefix/lib" -DFS_SUPPORT=ON \
  -DDEBUG_SUPPORT=OFF -DLOG_SUPPORT=OFF -DDIGEST_SUPPORT=OFF \
  -DUBUS_SUPPORT=OFF -DUCI_SUPPORT=OFF -DULOOP_SUPPORT=OFF \
  -DRTNL_SUPPORT=OFF -DNL80211_SUPPORT=OFF
cmake --build "$work/ucode-build" -j2
cmake --install "$work/ucode-build"
cmake -S "$work/lucihttp" -B "$work/lucihttp-build" \
  -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_RPATH="$prefix/lib" \
  -DCMAKE_C_FLAGS="-I$prefix/include" -DCMAKE_SHARED_LINKER_FLAGS="-L$prefix/lib" \
  -DBUILD_LUA=OFF -DBUILD_UCODE=ON -DBUILD_TESTS=OFF
cmake --build "$work/lucihttp-build" -j2
cmake --install "$work/lucihttp-build"

mkdir -p "$work/modules/luci"
http="$work/modules/luci/http.uc"
curl --fail --location --retry 3 \
  https://raw.githubusercontent.com/coolsnowwolf/luci/e881fed794a36dd18f282a4e227b7a1ced5679e5/modules/luci-base/ucode/http.uc \
  -o "$http"
export LD_LIBRARY_PATH="$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
LUCI_HTTP_FIXTURE="$http" python3 -m unittest discover -s "$root/tests/luci-http" -p 'test_*.py' -v
"$prefix/bin/ucode" -L "$work/modules" -D baseline=true "$root/tests/luci-http/multipart.uc"
python3 "$root/scripts/luci-multipart-limit.py" apply "$http"
python3 "$root/scripts/luci-multipart-limit.py" apply "$http"
"$prefix/bin/ucode" -L "$work/modules" -D baseline=false "$root/tests/luci-http/multipart.uc"
printf 'Native HTTP regression passed; isolated files: %s\n' "$work"
