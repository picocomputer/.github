# irm | iex runs this text in the user's session, where exit closes the
# window. The script block keeps the variables local, and throw stops it.
& {
    $ErrorActionPreference = 'Stop'
    # Windows PowerShell 5.1 can default to TLS 1.0, and GitHub supports only
    # TLS 1.2 and later.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    # CMake extracts the .7z archive, so 7-Zip is not needed.
    if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
        throw 'llvm-mos install: Install CMake first: winget install -e --id Kitware.CMake'
    }

    $compilers = $env:PICOCOMPUTER_COMPILERS
    if (-not $compilers) { $compilers = 'https://raw.githubusercontent.com/picocomputer/.github/main/compilers.json' }
    if (Test-Path -LiteralPath $compilers) {
        $url = (Get-Content -Raw -LiteralPath $compilers | ConvertFrom-Json).'llvm-mos'.downloads.windows
    } else {
        $url = (Invoke-RestMethod $compilers).'llvm-mos'.downloads.windows
    }

    $root = Join-Path $env:USERPROFILE '.rp6502'
    $dir = Join-Path $root 'llvm-mos'
    $tmp = Join-Path $root ('llvm-mos.' + [IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $tmp | Out-Null
    try {
        Write-Host "llvm-mos install: The download URL is $url."
        $archive = Join-Path $tmp 'llvm-mos.7z'
        curl.exe -fsSL -o $archive $url
        if ($LASTEXITCODE) { throw 'llvm-mos install: The download failed.' }
        cmake -E chdir $tmp cmake -E tar xf $archive
        if ($LASTEXITCODE) { throw 'llvm-mos install: The extraction failed.' }
        if (-not (Test-Path -LiteralPath (Join-Path $tmp 'llvm-mos\bin'))) {
            throw 'llvm-mos install: The downloaded archive contains no llvm-mos folder.'
        }
        if (Test-Path -LiteralPath $dir) { Remove-Item -Recurse -Force -LiteralPath $dir }
        Move-Item -LiteralPath (Join-Path $tmp 'llvm-mos') -Destination $dir
    } finally {
        Remove-Item -Recurse -Force -LiteralPath $tmp
    }
    Write-Host "llvm-mos install: llvm-mos is installed in $dir."

    # At the end of Path, because the llvm-mos bin folder contains a clang that
    # must not replace the system clang.
    $bin = Join-Path $dir 'bin'
    $path = [Environment]::GetEnvironmentVariable('Path', 'User')
    if (($path -split ';') -notcontains $bin) {
        [Environment]::SetEnvironmentVariable('Path', "$path;$bin".TrimStart(';'), 'User')
        Write-Host "llvm-mos install: $bin was added to the end of the user Path."
    }
    if (($env:Path -split ';') -notcontains $bin) { $env:Path = "$env:Path;$bin" }

    & (Join-Path $bin 'mos-rp6502-clang.bat') --version
    Write-Host 'llvm-mos install: Open a new terminal and restart VS Code so the new Path takes effect.'
}
