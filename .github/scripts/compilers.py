#!/usr/bin/env python3

import datetime
import json
import os
import re
import urllib.request

START, END = "<!-- compilers:start -->", "<!-- compilers:end -->"


def get(path):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "picocomputer-compilers"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    req = urllib.request.Request("https://api.github.com/" + path,
                                 headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def resolve(upstream, ref):
    ahead = get(f"repos/{upstream}/compare/"
                f"{ref}...picocomputer:{ref}")["ahead_by"]
    pulls, page = [], 1
    while True:
        batch = get(f"repos/{upstream}/pulls?state=open&per_page=100"
                    f"&page={page}")
        pulls += [{"number": p["number"], "title": p["title"],
                   "url": p["html_url"]}
                  for p in batch if p["user"]["login"] == "rumbledethumps"]
        if len(batch) < 100:
            break
        page += 1
    pulls.sort(key=lambda p: p["number"])
    fork = ahead > 0 or len(pulls) > 0
    repository = "picocomputer/" + upstream.split("/")[1] if fork else upstream
    return {"repository": repository, "ref": ref, "fork": fork,
            "ahead": ahead, "pulls": pulls}


def link(p):
    title = re.sub(r"([\\`*_\[\]<>])", r"\\\1", p["title"])
    return f"[#{p['number']} {title}]({p['url']})"


def bullet(name, c):
    notes = []
    if c["ahead"]:
        notes.append(f"The fork contains {c['ahead']} "
                     f"commit{'' if c['ahead'] == 1 else 's'} "
                     "not in the upstream repository.")
    if c["pulls"]:
        notes.append("The open pull requests to the upstream repository are "
                     f"{', '.join(link(p) for p in c['pulls'])}.")
    if not notes:
        notes.append("The upstream repository contains every Picocomputer "
                     "change.")
    r = c["repository"]
    return (f"- **{name}**: [{r}](https://github.com/{r}), "
            f"branch `{c['ref']}`. {' '.join(notes)}")


cc65 = resolve("cc65/cc65", "master")
cc65["downloads"] = {"windows": (
    "https://github.com/picocomputer/cc65/releases/download/prerelease/"
    "cc65-snapshot-win64.zip" if cc65["fork"] else
    "https://sourceforge.net/projects/cc65/files/cc65-snapshot-win64.zip/"
    "download")}
mos = resolve("llvm-mos/llvm-mos-sdk", "main")
base = (f"https://github.com/{mos['repository']}/releases/download/"
        "prerelease/llvm-mos-")
mos["downloads"] = {"windows": base + "windows.7z",
                    "macos": base + "macos.tar.xz",
                    "linux": base + "linux.tar.xz"}

today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
block = (f"Last checked on {today}.\n\n"
         f"{bullet('cc65', cc65)} The Windows build is "
         f"[cc65-snapshot-win64.zip]({cc65['downloads']['windows']}). "
         "On Linux and macOS, the install script builds cc65 from this "
         "repository.\n\n"
         f"{bullet('llvm-mos', mos)} The builds are for "
         f"[Windows]({mos['downloads']['windows']}), "
         f"[macOS]({mos['downloads']['macos']}) and "
         f"[Linux]({mos['downloads']['linux']}).")
with open("profile/README.md", encoding="utf-8") as f:
    readme = f.read()
start, end = readme.index(START) + len(START), readme.index(END)
readme = readme[:start] + "\n" + block + "\n" + readme[end:]

with open("compilers.json", "w", encoding="utf-8") as f:
    f.write(json.dumps({"cc65": cc65, "llvm-mos": mos}, indent=2) + "\n")
with open("profile/README.md", "w", encoding="utf-8") as f:
    f.write(readme)
