## Documentation

**Start here**: [picocomputer.github.io](https://picocomputer.github.io/)<br/>

## Binary Downloads

- [Firmware and emulators](https://github.com/picocomputer/rp6502/releases/latest):
  the Pi Pico 2 firmware and all emulator binaries.
- [Example programs](https://github.com/picocomputer/examples/releases/latest):
  simple ROMs built from the examples repository.
- [Microsoft BASIC](https://github.com/picocomputer/msbasic/releases/latest):
  enhanced with our line editor and more token space.

## Compilers

The Picocomputer SDK builds programs with cc65 or llvm-mos. New Picocomputer
features are often added to these compilers before their next release, so the
compiler has to be a recent build. The curl and irm commands in the
[RP6502-SDK](https://picocomputer.github.io/sdk.html#sdk-install).
are currently routed according to the logic below. If the date isn't
updating every day, something went wrong with the automation.

<!-- compilers:start -->
Last checked on 2026-09-26.

- **cc65**: [cc65/cc65](https://github.com/cc65/cc65), branch `master`. The upstream repository contains every Picocomputer change. The Windows build is [cc65-snapshot-win64.zip](https://sourceforge.net/projects/cc65/files/cc65-snapshot-win64.zip/download). On Linux and macOS, the install script builds cc65 from this repository.

- **llvm-mos**: [llvm-mos/llvm-mos-sdk](https://github.com/llvm-mos/llvm-mos-sdk), branch `main`. The upstream repository contains every Picocomputer change. The builds are for [Windows](https://github.com/llvm-mos/llvm-mos-sdk/releases/download/prerelease/llvm-mos-windows.7z), [macOS](https://github.com/llvm-mos/llvm-mos-sdk/releases/download/prerelease/llvm-mos-macos.tar.xz) and [Linux](https://github.com/llvm-mos/llvm-mos-sdk/releases/download/prerelease/llvm-mos-linux.tar.xz).
<!-- compilers:end -->
