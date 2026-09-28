#!/usr/bin/env python3
#
# Copyright (c) 2026 Rumbledethumps
#
# SPDX-License-Identifier: BSD-3-Clause OR Unlicense
#
"""Publishes the web zips that a repository's markdown names.

Each player is an HTML comment in a markdown file that git tracks:

    <!-- rp6502
    preset: cc65/Release
    publish: hello.zip
    -->

The CMake preset is built in a folder of its own, and hello.zip, which an
rp6502_web() call makes, is unpacked to <out>/hello/. The Linux emulator
of the same build runs the ROM for 120 frames, or the number given by the
frames key, and the screen is written to <out>/hello/screenshot.png, 640
pixels wide, for a README to show. Run it from the root of the
repository. The keys are described at https://picocomputer.github.io/web.html.
"""

import argparse
import html
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
import zlib

REQUIRED = ("preset", "publish")
SETTINGS = ("folder", "frames")
COMPILERS = ("cc65", "llvm-mos")
INSTALL_URL = "https://raw.githubusercontent.com/picocomputer/.github/main/install"
LATEST = "release picocomputer/rp6502 latest"


class WebError(Exception):
    pass


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True,
                          text=True).stdout


def read_blocks():
    """Every rp6502 block, with the file and line it starts on, and all the
    markdown text for the link check."""
    blocks = []
    text_all = []
    for path in git("ls-files", "-z", "*.md").split("\0"):
        if not path:
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        text_all.append(text)
        for m in re.finditer(r"<!--[ \t]*rp6502[ \t]*\n(.*?)-->", text, re.S):
            where = f"{path}:{text.count(chr(10), 0, m.start()) + 1}"
            blocks.append(parse_block(m.group(1), where))
    return blocks, "\n".join(text_all)


def parse_block(body, where):
    block = {"where": where}
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep:
            raise WebError(f"{where}: '{line}' is not 'key: value'")
        if key not in REQUIRED + SETTINGS:
            raise WebError(f"{where}: unknown key '{key}'; the keys are "
                           f"{', '.join(REQUIRED + SETTINGS)}, and the page is set "
                           "up by rp6502_web() in CMakeLists.txt")
        if key in block:
            raise WebError(f"{where}: '{key}' is given twice")
        block[key] = value
    for key in REQUIRED:
        if not block.get(key):
            raise WebError(f"{where}: '{key}' is missing")
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]*\.zip", block["publish"]):
        raise WebError(f"{where}: publish '{block['publish']}' is not a zip that "
                       "rp6502_web() makes, such as game.zip")
    block["name"] = block["publish"][:-len(".zip")]
    if not re.fullmatch(r"[1-9][0-9]*", block.get("frames", "1")):
        raise WebError(f"{where}: frames is a whole number above 0, such as 300")
    block.setdefault("folder", ".")
    return block


def use_compiler(preset, ci):
    """Puts the compiler for the preset on PATH, installing it in CI."""
    family = preset.split("/")[0]
    if family not in COMPILERS:
        return
    bin_dir = os.path.expanduser(f"~/.rp6502/{family}/bin")
    if ci and not os.path.isdir(bin_dir):
        url = f"{os.environ.get('PICOCOMPUTER_COMPILERS', INSTALL_URL)}/{family}.sh"
        print(f"Installing {family}", flush=True)
        subprocess.run(["bash", "-o", "pipefail", "-c", f'curl -fsSL "{url}" | sh'],
                       check=True)
    if os.path.isdir(bin_dir):
        # cc65 goes in front of any older copy; the llvm-mos folder holds a
        # clang that must not replace the system one.
        if family == "cc65":
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
        else:
            os.environ["PATH"] = os.environ["PATH"] + os.pathsep + bin_dir


def update_tools(folder):
    """The latest tools and emulator."""
    tools = os.path.join(folder, "tools")
    print(f"Updating {tools}", flush=True)
    subprocess.run(["cmake", "-P", os.path.join(tools, "rp6502.cmake")], check=True)


def build(folder, preset, build_dir, emulator):
    """Configures the preset of folder into build_dir, never the build folder
    of the project, and builds it."""
    print(f"Building {preset} in {folder}", flush=True)
    configure = ["cmake", "--preset", preset, "-B", build_dir]
    if emulator:
        configure.append(f"-DRP6502_WEB_EMULATOR={emulator}")
    if subprocess.run(configure, cwd=folder).returncode:
        raise WebError(f"cmake --preset {preset} failed in {folder}")
    if subprocess.run(["cmake", "--build", build_dir]).returncode:
        raise WebError(f"building {preset} failed in {folder}")


def unpack(zip_path, folder):
    """The zip unpacked into folder, refusing paths that would leave it."""
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            parts = name.replace("\\", "/").split("/")
            if name.startswith("/") or ".." in parts or ":" in parts[0]:
                raise WebError(f"{zip_path} has an unsafe path: {name}")
        if "index.html" not in archive.namelist():
            raise WebError(f"{zip_path} has no index.html at its root")
        archive.extractall(folder)


def page_config(page):
    """rom, args, install and title as the inline scripts of the page set
    them, the last one for a key winning. A value is read as a quoted
    string or an array of quoted strings, the forms rp6502_web() and the
    release page write."""
    with open(page, encoding="utf-8") as f:
        text = f.read()
    scripts = "\n".join(re.findall(r"<script>(.*?)</script>", text, re.S))
    string = r"'([^'\\]*)'|\"([^\"\\]*)\""
    config = {}
    for m in re.finditer(r"\b(rom|args|install|title)\s*[:=]\s*", scripts):
        key, rest = m.group(1), scripts[m.end():]
        one = re.match(string, rest)
        many = re.match(r"\[\s*((?:(?:" + string + r")\s*,?\s*)*)\]", rest)
        if key in ("rom", "title") and one:
            config[key] = one.group(1) if one.group(1) is not None else one.group(2)
        elif key in ("args", "install") and many:
            config[key] = [a if a else b for a, b in re.findall(string, many.group(1))]
        else:
            raise WebError(f"{page}: '{key}' is set to '{rest.splitlines()[0].strip()}', "
                           "which web.py does not read; write a quoted string, or an "
                           "array of them for args and install")
    if not config.get("rom"):
        raise WebError(f"{page} sets no CONFIG.rom")
    return config


def github(url, token=True):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    key = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and key:
        request.add_header("Authorization", f"Bearer {key}")
    return request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def download(url, token):
    """The file at url. An artifact answers with a redirect to the storage
    host, which is followed without the token."""
    try:
        opener = urllib.request.build_opener(NoRedirect)
        with opener.open(github(url, token), timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            raise
        with urllib.request.urlopen(e.headers["Location"], timeout=120) as response:
            return response.read()


def fetch_linux_emulator(source, where, tmp):
    """rp6502-emu from the Linux build that goes with the web zip of a
    player, as rp6502_web() recorded it, or None."""
    if source.startswith("file "):
        print(f"warning: {where}: the emulator is {source[5:]}, so the screenshot "
              "uses the Linux emulator of the latest release", file=sys.stderr)
        source = LATEST
    kind, repo, ref = source.split()
    suffix = f"-linux-{platform.machine()}.tar.gz"
    if platform.system() != "Linux":
        print("warning: the players have no screenshots, because this computer "
              "runs no Linux emulator", file=sys.stderr)
        return None
    api = f"https://api.github.com/repos/{repo}"
    if kind == "release":
        info = json.load(urllib.request.urlopen(
            github(f"{api}/releases/" + ("latest" if ref == "latest" else f"tags/{ref}")),
            timeout=60))
        urls = [a["browser_download_url"] for a in info["assets"] if a["name"].endswith(suffix)]
        token = False
    else:
        info = json.load(urllib.request.urlopen(
            github(f"{api}/actions/runs/{ref}/artifacts?per_page=100"), timeout=60))
        urls = [f"{api}/actions/artifacts/{a['id']}/zip" for a in info["artifacts"]
                if a["name"].endswith(suffix) and not a["expired"]]
        token = True
    if len(urls) != 1:
        print(f"warning: {where}: {source} has no {suffix}, so there is no screenshot",
              file=sys.stderr)
        return None
    print(f"Fetching the Linux emulator of {source}", flush=True)
    with tarfile.open(fileobj=io.BytesIO(download(urls[0], token))) as tar:
        data = tar.extractfile("rp6502-emu").read()
    emu = os.path.join(tmp, re.sub(r"[^A-Za-z0-9]", "_", source))
    with open(emu, "wb") as f:
        f.write(data)
    os.chmod(emu, 0o755)
    return emu


def screenshot(emu, block, folder, config):
    """Runs the ROM, install files and arguments of the page for the frames
    of the block, and writes the screen to screenshot.png."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "raw.png")
        # A fixed seed and an empty save folder give the same screenshot on
        # every run, and a local run neither reads nor writes the real saves.
        command = [emu, "--screenshot", raw, "--seed", "1",
                   "--save-dir", os.path.join(tmp, "saves")]
        if "frames" in block:
            command += ["--frames", block["frames"]]
        for path in config.get("install", []):
            command += ["--install", os.path.join(folder, path)]
        command.append(os.path.join(folder, config["rom"]))
        if config.get("args"):
            command += ["--", *config["args"]]
        if subprocess.run(command, stdout=subprocess.DEVNULL).returncode:
            raise WebError(f"{block['where']}: the emulator wrote no screenshot")
        write_wide_png(raw, os.path.join(folder, "screenshot.png"))


def write_wide_png(raw, png):
    """The emulator's PNG, which is uncompressed RGBA, as a compressed RGB
    PNG 640 pixels wide. A canvas is 320 or 640 pixels wide, and a 320 one
    is doubled both ways."""
    with open(raw, "rb") as f:
        data = f.read()
    pos, idat = 8, []
    while pos < len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height = int.from_bytes(body[0:4], "big"), int.from_bytes(body[4:8], "big")
            form = body[8:]
        elif kind == b"IDAT":
            idat.append(body)
        pos += 12 + length
    pixels = zlib.decompress(b"".join(idat))
    stride = width * 4 + 1
    if form != bytes([8, 6, 0, 0, 0]) or width not in (320, 640) or \
            any(pixels[y * stride] for y in range(height)):
        raise WebError(f"{raw} is not an emulator screenshot")
    scale = 640 // width
    rows = []
    for y in range(height):
        rgba = pixels[y * stride + 1:(y + 1) * stride]
        rgb = bytearray(1 + 640 * 3)
        for c in range(3):
            for s in range(scale):
                rgb[1 + c + 3 * s::3 * scale] = rgba[c::4]
        rows += [rgb] * scale

    def chunk(kind, body):
        return (len(body).to_bytes(4, "big") + kind + body
                + zlib.crc32(kind + body).to_bytes(4, "big"))
    header = (640).to_bytes(4, "big") + (height * scale).to_bytes(4, "big") + bytes([8, 2, 0, 0, 0])
    with open(png, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ci", action="store_true",
                        help="install the compilers the presets need")
    parser.add_argument("--update-tools", action="store_true",
                        help="build with the latest tools, as a template's CI does")
    parser.add_argument("--emulator", default="",
                        help="the web zip for every rp6502_web(), as its EMULATOR takes it")
    parser.add_argument("--out", default="build/web", help="site folder (default: build/web)")
    args = parser.parse_args()

    blocks, markdown = read_blocks()
    if not blocks:
        raise WebError("no <!-- rp6502 --> blocks in the markdown")
    for b in blocks:
        same = [o["where"] for o in blocks if o["name"] == b["name"]]
        if len(same) > 1:
            raise WebError(f"{' and '.join(same)} both publish {b['publish']}")

    if args.update_tools:
        for folder in dict.fromkeys(b["folder"] for b in blocks):
            update_tools(folder)

    shutil.rmtree(args.out, ignore_errors=True)
    os.makedirs(args.out)
    items = []
    with tempfile.TemporaryDirectory() as tmp:
        built = {}
        emulators = {}
        for block in blocks:
            folder, preset = block["folder"], block["preset"]
            if (folder, preset) not in built:
                use_compiler(preset, args.ci)
                build_dir = os.path.join(tmp, f"build{len(built)}")
                build(folder, preset, build_dir, args.emulator)
                built[(folder, preset)] = build_dir
            web = os.path.join(built[(folder, preset)], "web")
            zip_path = os.path.join(web, block["publish"])
            if not os.path.isfile(zip_path):
                raise WebError(f"{block['where']}: building {preset} in {folder} made no "
                               f"{block['publish']}; rp6502_web(<rom> OUTPUT "
                               f"{block['publish']}) in CMakeLists.txt makes it")
            site = os.path.join(args.out, block["name"])
            unpack(zip_path, site)
            config = page_config(os.path.join(site, "index.html"))
            with open(os.path.join(web, block["name"] + ".emulator")) as f:
                source = f.read().strip()
            if source not in emulators:
                emulators[source] = fetch_linux_emulator(source, block["where"], tmp)
            if emulators[source]:
                screenshot(emulators[source], block, site, config)
            title = config.get("title") or block["name"]
            items.append(f'  <li><a href="{html.escape(block["name"])}/">{html.escape(title)}</a></li>')
            if not re.search(rf"github\.io/[^\s)\"']*?/{re.escape(block['name'])}/?[\s)\"']",
                             markdown):
                print(f"warning: {block['where']}: no link to the {block['name']} player",
                      file=sys.stderr)
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n<html lang=\"en\">\n<meta charset=\"utf-8\">\n"
                "<title>Web players</title>\n<ul>\n" + "\n".join(items) + "\n</ul>\n")
    for block in blocks:
        print(f"{block['name']}/ from {block['publish']}, {block['preset']}")
    print(f"Site in {args.out}")


if __name__ == "__main__":
    try:
        main()
    except (WebError, subprocess.CalledProcessError, urllib.error.URLError) as e:
        sys.exit(f"web.py: {e}")
