#!/bin/sh

# The braces make sh read the whole script before running any of it, so a
# download from curl that stops partway runs nothing.
{
set -eu

info() { echo "cc65 install: $*"; }
fail() { echo "cc65 install: $*" >&2; exit 1; }

os=$(uname -s)
if [ "$os" = Darwin ]; then
    deps="xcode-select --install"
else
    deps="sudo apt install git build-essential python3"
fi
for tool in git make gcc python3; do
    command -v "$tool" >/dev/null || fail "$tool is missing. Install it with: $deps"
done

json=$(curl -fsSL "${PICOCOMPUTER_COMPILERS:-https://raw.githubusercontent.com/picocomputer/.github/main/compilers.json}")
field() {
    printf '%s\n' "$json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cc65"][sys.argv[1]])' "$1"
}
repository=$(field repository)
ref=$(field ref)

root="$HOME/.rp6502"
mkdir -p "$root"
tmp=$(mktemp -d "$root/cc65.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
# dash skips the EXIT trap when a signal ends the shell.
trap 'exit 1' HUP INT TERM

info "The source is https://github.com/$repository.git at $ref."
git clone --depth 1 --branch "$ref" "https://github.com/$repository.git" "$tmp/cc65"
# cc65 searches for the include, lib and target folders relative to the bin
# folder, so the build tree is a working install and make install is not needed.
make -C "$tmp/cc65" -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)"
# The object files in libwrk and wrk are only used by the build.
rm -rf "$tmp/cc65/.git" "$tmp/cc65/libwrk" "$tmp/cc65/wrk"
rm -rf "$root/cc65"
mv "$tmp/cc65" "$root/cc65"
info "cc65 is installed in $root/cc65."

# A login bash skips ~/.profile when ~/.bash_profile exists.
if [ -f "$HOME/.bash_profile" ]; then
    profile="$HOME/.bash_profile"
else
    profile="$HOME/.profile"
fi
if [ "$os" = Darwin ]; then
    case ${SHELL:-} in
    *bash) ;;
    *) profile="$HOME/.zprofile" ;;
    esac
    note="Open a new terminal and restart VS Code so the new PATH takes effect."
else
    note="Log out and back in so the new PATH takes effect."
fi
# At the front of PATH, so an older cc65 elsewhere on PATH is not used.
line='export PATH="$HOME/.rp6502/cc65/bin:$PATH"'
if ! grep -qsF .rp6502/cc65/bin "$profile"; then
    # The blank line keeps a last line with no newline from joining this one.
    printf '\n%s\n' "$line" >>"$profile"
    info "This line was added to $profile: $line"
fi

"$root/cc65/bin/cl65" --version
info "$note"
}
