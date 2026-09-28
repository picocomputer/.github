#!/usr/bin/env python3
#
# Copyright (c) 2026 Rumbledethumps
#
# SPDX-License-Identifier: BSD-3-Clause OR Unlicense
#
"""Builds the web players that a repository's markdown asks for.

Each player is an HTML comment in a markdown file that git tracks:

    <!-- rp6502
    preset: cc65/Release
    target: hello
    -->

The target is built with the CMake preset, and the player is written to
<out>/<target>/index.html, with rp6502.js and rp6502.wasm from the itch.io
zip of an rp6502 release in <out>. Run it from the root of the repository.
The project's own tools/ are used as committed, including BASIC in
tools/basic.rp6502, unless --update-tools asks for the latest of each.
The keys are described at https://picocomputer.github.io/web.html.
"""

import argparse
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

REQUIRED = ("preset", "target")
SETTINGS = ("folder", "title", "args", "install", "image", "db", "bg",
            "filter", "overlay")
COMPILERS = ("cc65", "llvm-mos")
INSTALL_URL = "https://raw.githubusercontent.com/picocomputer/.github/main/install"


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
    block = {"where": where, "footer": []}
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep:
            raise WebError(f"{where}: '{line}' is not 'key: value'")
        if key == "footer":
            block["footer"].append(value)
        elif key not in REQUIRED + SETTINGS:
            raise WebError(f"{where}: unknown key '{key}'")
        elif key in block:
            raise WebError(f"{where}: '{key}' is given twice")
        else:
            block[key] = value
    for key in REQUIRED:
        if not block.get(key):
            raise WebError(f"{where}: '{key}' is missing")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", block["target"]):
        raise WebError(f"{where}: target '{block['target']}' cannot be a folder name on the site")
    if block.get("overlay", "no") not in ("yes", "no"):
        raise WebError(f"{where}: overlay is yes or no")
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
    """The latest tools and emulator, and the latest BASIC release, which
    the next configure fetches because tools/basic.rp6502 is gone."""
    tools = os.path.join(folder, "tools")
    print(f"Updating {tools}", flush=True)
    subprocess.run(["cmake", "-P", os.path.join(tools, "rp6502.cmake")], check=True)
    basic = os.path.join(tools, "basic.rp6502")
    if os.path.exists(basic):
        os.remove(basic)


def build(folder, preset):
    """Configures and builds the preset in folder, and returns the build
    folder that CMake reports."""
    print(f"Building {preset} in {folder}", flush=True)
    run = subprocess.run(["cmake", "--preset", preset], cwd=folder,
                         capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stdout.write(run.stderr)
    if run.returncode:
        raise WebError(f"cmake --preset {preset} failed in {folder}")
    m = re.search(r"^-- Build files have been written to: (.+)$", run.stdout, re.M)
    if not m:
        raise WebError(f"cmake --preset {preset} in {folder} names no build folder")
    if subprocess.run(["cmake", "--build", "--preset", preset], cwd=folder).returncode:
        raise WebError(f"cmake --build --preset {preset} failed in {folder}")
    return os.path.join(folder, m.group(1).strip())


def find_rom(build_dir, block):
    """The one <target>.rp6502 ROM in the build folder. CMakeFiles holds
    folders with that name and other programs, so it is skipped."""
    name = block["target"] + ".rp6502"
    found = []
    for dirpath, dirnames, filenames in os.walk(build_dir):
        dirnames[:] = [d for d in dirnames if d != "CMakeFiles"]
        if name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, "rb") as f:
                if f.read(8) == b"#!RP6502":
                    found.append(path)
    if len(found) != 1:
        raise WebError(f"{block['where']}: {len(found)} copies of {name} in "
                       f"{build_dir} after building {block['preset']}, not 1")
    return found[0]


def github_json(url):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def fetch_emulator(release):
    """rp6502.js, rp6502.wasm and index.html from the itch.io zip."""
    api = "https://api.github.com/repos/picocomputer/rp6502/releases/"
    info = github_json(api + ("latest" if release == "latest" else f"tags/{release}"))
    urls = [a["browser_download_url"] for a in info["assets"]
            if a["name"].endswith("-itch.io.zip")]
    if len(urls) != 1:
        raise WebError(f"rp6502 release {info['tag_name']} has no itch.io zip")
    print(f"Fetching the emulator from {info['tag_name']}", flush=True)
    with urllib.request.urlopen(urls[0], timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    return {name: archive.read(name) for name in ("rp6502.js", "rp6502.wasm", "index.html")}


def repository():
    """owner/name, from GitHub Actions or the origin remote."""
    if os.environ.get("GITHUB_REPOSITORY"):
        return os.environ["GITHUB_REPOSITORY"]
    url = git("remote", "get-url", "origin").strip()
    m = re.search(r"github\.com[:/](.+?/.+?)(\.git)?$", url)
    return m.group(1) if m else ""


def page(template, block, files, repo):
    """The player's index.html: the release's page with CONFIG, the footer
    and the path to rp6502.js filled in."""
    words = lambda key: block.get(key, "").split()
    config = {
        "title": block.get("title", ""),
        "rom": files[0],
        "args": words("args"),
        "install": [os.path.basename(p) for p in words("install")],
        "db": block.get("db", ""),
        "bg": block.get("bg", ""),
        "filter": block.get("filter", ""),
        "overlay": "overlay" if block.get("overlay") == "yes" else "",
        "footer": "footer" if block["footer"] else "",
        "image": os.path.basename(block["image"]) if "image" in block else "",
    }
    lines = "".join(f"\n    {json.dumps(k)}: {json.dumps(v)}," for k, v in config.items())
    text, n = re.subn(r"var CONFIG = \{.*?\};", lambda m: "var CONFIG = {" + lines + "\n  };",
                      template, count=1, flags=re.S)
    if n != 1:
        raise WebError("the release's index.html has no CONFIG")
    credits = '<a href="https://picocomputer.github.io" target="_blank">Picocomputer 6502</a>'
    if repo:
        credits = (f'<a href="https://github.com/{html.escape(repo)}" target="_blank">'
                   f"{html.escape(repo)}</a> &middot; " + credits)
    footer = ('<div class="footer">'
              + "".join(f"\n    <p>{html.escape(line)}</p>" for line in block["footer"])
              + f'\n    <p class="credits">{credits}</p>\n  </div>')
    text, n = re.subn(r'(<template id="footer">).*?(</template>)',
                      lambda m: m.group(1) + "\n  " + footer + "\n" + m.group(2),
                      text, count=1, flags=re.S)
    if n != 1:
        raise WebError("the release's index.html has no footer template")
    if 'src="rp6502.js"' not in text:
        raise WebError("the release's index.html does not load rp6502.js")
    return text.replace('src="rp6502.js"', 'src="../rp6502.js"')


def write_site(out, emulator, players, repo):
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for name in ("rp6502.js", "rp6502.wasm"):
        with open(os.path.join(out, name), "wb") as f:
            f.write(emulator[name])
    template = emulator["index.html"].decode("utf-8")
    items = []
    for block, files in players:
        folder = os.path.join(out, block["target"])
        os.makedirs(folder)
        for path in files:
            shutil.copy2(path, folder)
        names = [os.path.basename(p) for p in files]
        with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as f:
            f.write(page(template, block, names, repo))
        title = block.get("title") or block["target"]
        items.append(f'  <li><a href="{block["target"]}/">{html.escape(title)}</a></li>')
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n<html lang=\"en\">\n<meta charset=\"utf-8\">\n"
                "<title>Web players</title>\n<ul>\n" + "\n".join(items) + "\n</ul>\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ci", action="store_true",
                        help="install the compilers the presets need")
    parser.add_argument("--update-tools", action="store_true",
                        help="build with the latest tools and BASIC, as a template's CI does")
    parser.add_argument("--rp6502", default="latest",
                        help="rp6502 release tag for the emulator (default: latest)")
    parser.add_argument("--out", default="build/web", help="site folder (default: build/web)")
    args = parser.parse_args()

    blocks, markdown = read_blocks()
    if not blocks:
        raise WebError("no <!-- rp6502 --> blocks in the markdown")
    targets = [b["target"] for b in blocks]
    for b in blocks:
        if targets.count(b["target"]) > 1:
            raise WebError(f"{b['where']}: target '{b['target']}' is used twice")

    if args.update_tools:
        for folder in dict.fromkeys(b["folder"] for b in blocks):
            update_tools(folder)

    built = {}
    players = []
    for block in blocks:
        folder, preset = block["folder"], block["preset"]
        if (folder, preset) not in built:
            use_compiler(preset, args.ci)
            built[(folder, preset)] = build(folder, preset)
        files = [find_rom(built[(folder, preset)], block)]
        files += [os.path.join(folder, p) for p in block.get("install", "").split()]
        if "image" in block:
            files.append(os.path.join(folder, block["image"]))
        names = [os.path.basename(p).lower() for p in files]
        for path in files:
            if not os.path.isfile(path):
                raise WebError(f"{block['where']}: {path} is not a file")
            if names.count(os.path.basename(path).lower()) > 1:
                raise WebError(f"{block['where']}: two files are named {os.path.basename(path)}")
        players.append((block, files))
        if not re.search(rf"github\.io/[^\s)\"']*?/{re.escape(block['target'])}/?[\s)\"']",
                         markdown):
            print(f"warning: {block['where']}: no link to the {block['target']} player",
                  file=sys.stderr)

    write_site(args.out, fetch_emulator(args.rp6502), players, repository())
    for block, _ in players:
        print(f"{block['target']}/ from {block['preset']}")
    print(f"Site in {args.out}")


if __name__ == "__main__":
    try:
        main()
    except (WebError, subprocess.CalledProcessError, urllib.error.URLError) as e:
        sys.exit(f"web.py: {e}")
