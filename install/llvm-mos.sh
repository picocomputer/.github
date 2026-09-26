#!/bin/sh

# The braces make sh read the whole script before running any of it, so a
# download from curl that stops partway runs nothing.
{
set -eu

info() { echo "llvm-mos install: $*"; }
fail() { echo "llvm-mos install: $*" >&2; exit 1; }

os=$(uname -s)
if [ "$os" = Darwin ]; then
    platform=macos
else
    platform=linux
    arch=$(uname -m)
    [ "$arch" = x86_64 ] || fail "The prebuilt llvm-mos compiler for Linux is x86-64 only, and this machine is $arch."
fi

json=$(curl -fsSL "${PICOCOMPUTER_COMPILERS:-https://raw.githubusercontent.com/picocomputer/.github/main/compilers.json}")
url=$(printf '%s\n' "$json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["llvm-mos"]["downloads"][sys.argv[1]])' "$platform")

root="$HOME/.rp6502"
mkdir -p "$root"
tmp=$(mktemp -d "$root/llvm-mos.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
# dash skips the EXIT trap when a signal ends the shell.
trap 'exit 1' HUP INT TERM

info "The download URL is $url."
curl -fsSL "$url" | tar -xJ -C "$tmp"
# tar on macOS exits with success on the empty output of a failed curl, so
# the missing folder is the only sign of the failure.
[ -d "$tmp/llvm-mos/bin" ] || fail "The downloaded archive contains no llvm-mos folder."
rm -rf "$root/llvm-mos"
mv "$tmp/llvm-mos" "$root/llvm-mos"
info "llvm-mos is installed in $root/llvm-mos."

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
# At the end of PATH, because the llvm-mos bin folder contains a clang that
# must not replace the system clang.
line='export PATH="$PATH:$HOME/.rp6502/llvm-mos/bin"'
if ! grep -qsF .rp6502/llvm-mos/bin "$profile"; then
    # The blank line keeps a last line with no newline from joining this one.
    printf '\n%s\n' "$line" >>"$profile"
    info "This line was added to $profile: $line"
fi

"$root/llvm-mos/bin/mos-rp6502-clang" --version
info "$note"
}
