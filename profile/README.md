# Picocomputer 6502

**Start here: [picocomputer.github.io](https://picocomputer.github.io/)**

The documentation and the guide to writing programs.

## Downloads

- [Firmware and emulators](https://github.com/picocomputer/rp6502/releases/latest):
  the Pico firmware, and the emulator for Windows, macOS, Linux, RetroArch,
  Android and the Analogue Pocket.
- [Example programs](https://github.com/picocomputer/examples/releases/latest):
  ROMs and tools built from the examples repository.
- [Microsoft BASIC](https://github.com/picocomputer/msbasic/releases/latest):
  `basic.rp6502`.

## Compilers

The Picocomputer SDK builds programs with cc65 or llvm-mos. New Picocomputer
features are often added to these compilers before their next release, so the
compiler has to be a recent build. The cc65 and llvm-mos packages in apt,
Homebrew, MacPorts and other package managers are too old. The other tools,
such as CMake and Python, do not need to be this current.

On Linux and macOS:

```sh
curl -fsSL https://raw.githubusercontent.com/picocomputer/.github/main/install/cc65.sh | sh
curl -fsSL https://raw.githubusercontent.com/picocomputer/.github/main/install/llvm-mos.sh | sh
```

On Windows, in PowerShell:

```powershell
irm https://raw.githubusercontent.com/picocomputer/.github/main/install/cc65.ps1 | iex
irm https://raw.githubusercontent.com/picocomputer/.github/main/install/llvm-mos.ps1 | iex
```

Each command installs the best build at the moment into `.rp6502` in the home
folder and adds it to PATH. Run the command again to update. The other tools
and their install steps are in
[RP6502-SDK](https://picocomputer.github.io/sdk.html#sdk-install).

The builds are made from the repositories below. This list is checked and
updated automatically once a day, and the install commands use the same
repositories.

<!-- compilers:start -->
Last checked on 2026-09-26.

- **cc65**: [cc65/cc65](https://github.com/cc65/cc65), branch `master`. The upstream repository contains every Picocomputer change. The Windows build is [cc65-snapshot-win64.zip](https://sourceforge.net/projects/cc65/files/cc65-snapshot-win64.zip/download). On Linux and macOS, the install script builds cc65 from this repository.

- **llvm-mos**: [llvm-mos/llvm-mos-sdk](https://github.com/llvm-mos/llvm-mos-sdk), branch `main`. The upstream repository contains every Picocomputer change. The builds are for [Windows](https://github.com/llvm-mos/llvm-mos-sdk/releases/download/prerelease/llvm-mos-windows.7z), [macOS](https://github.com/llvm-mos/llvm-mos-sdk/releases/download/prerelease/llvm-mos-macos.tar.xz) and [Linux](https://github.com/llvm-mos/llvm-mos-sdk/releases/download/prerelease/llvm-mos-linux.tar.xz).
<!-- compilers:end -->
