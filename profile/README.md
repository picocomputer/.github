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
[RP6502-SDK](https://picocomputer.github.io/sdk.html#sdk-install)
are currently routed according to the logic below. If the date isn't
updating every day, something went wrong with the automation.

<!-- compilers:start -->
Last checked on 2026-10-01 UTC.

- **cc65**: [picocomputer/cc65](https://github.com/picocomputer/cc65), branch `master`. The fork contains 4 commits not in the upstream repository. The Windows build is [cc65-snapshot-win64.zip](https://github.com/picocomputer/cc65/releases/download/prerelease/cc65-snapshot-win64.zip). On Linux and macOS, the install script builds cc65 from this repository.

- **llvm-mos**: [picocomputer/llvm-mos-sdk](https://github.com/picocomputer/llvm-mos-sdk), branch `main`. The fork contains 2 commits not in the upstream repository. The builds are for [Windows](https://github.com/picocomputer/llvm-mos-sdk/releases/download/prerelease/llvm-mos-windows.7z), [macOS](https://github.com/picocomputer/llvm-mos-sdk/releases/download/prerelease/llvm-mos-macos.tar.xz) and [Linux](https://github.com/picocomputer/llvm-mos-sdk/releases/download/prerelease/llvm-mos-linux.tar.xz).
<!-- compilers:end -->
