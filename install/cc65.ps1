# irm | iex runs this text in the user's session, where exit closes the
# window. The script block keeps the variables local, and throw stops it.
& {
    $ErrorActionPreference = 'Stop'
    # Windows PowerShell 5.1 can default to TLS 1.0, and GitHub supports only
    # TLS 1.2 and later.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $base = $env:PICOCOMPUTER_COMPILERS
    if (-not $base) { $base = 'https://raw.githubusercontent.com/picocomputer/.github/main/install' }
    if (Test-Path -LiteralPath $base) {
        $repository = (Get-Content -Raw -LiteralPath (Join-Path $base 'cc65.txt')).Trim()
    } else {
        $repository = (Invoke-RestMethod "$base/cc65.txt").Trim()
    }
    # Upstream cc65 publishes its Windows build only on SourceForge.
    if ($repository -eq 'cc65/cc65') {
        $url = 'https://sourceforge.net/projects/cc65/files/cc65-snapshot-win64.zip/download'
    } else {
        $url = "https://github.com/$repository/releases/download/prerelease/cc65-snapshot-win64.zip"
    }

    $root = Join-Path $env:USERPROFILE '.rp6502'
    $dir = Join-Path $root 'cc65'
    $tmp = Join-Path $root ('cc65.' + [IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $tmp | Out-Null
    try {
        Write-Host "cc65 install: The download URL is $url."
        $zip = Join-Path $tmp 'cc65.zip'
        # For the PowerShell user agent, SourceForge serves an HTML page instead
        # of the file. For curl, SourceForge serves a redirect to the file.
        curl.exe -fsSL -o $zip $url
        if ($LASTEXITCODE) { throw 'cc65 install: The download failed.' }
        Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $tmp 'cc65')
        if (Test-Path -LiteralPath $dir) { Remove-Item -Recurse -Force -LiteralPath $dir }
        Move-Item -LiteralPath (Join-Path $tmp 'cc65') -Destination $dir
    } finally {
        Remove-Item -Recurse -Force -LiteralPath $tmp
    }
    Write-Host "cc65 install: cc65 is installed in $dir."

    # At the front of the user Path, so an older cc65 later in the user Path is
    # not used.
    $bin = Join-Path $dir 'bin'
    $path = [Environment]::GetEnvironmentVariable('Path', 'User')
    if (($path -split ';') -notcontains $bin) {
        [Environment]::SetEnvironmentVariable('Path', "$bin;$path".TrimEnd(';'), 'User')
        Write-Host "cc65 install: $bin was added to the front of the user Path."
    }
    if (($env:Path -split ';') -notcontains $bin) { $env:Path = "$bin;$env:Path" }

    # cl65 prints the version line on stderr. In hosts that capture stderr, such
    # as the ISE, Windows PowerShell 5.1 converts each stderr line into an
    # error, and 'Stop' makes that error fatal. With 2>&1 and Write-Host, every
    # host prints the same plain line.
    $ErrorActionPreference = 'Continue'
    Write-Host (& (Join-Path $bin 'cl65.exe') --version 2>&1)
    Write-Host 'cc65 install: Open a new terminal and restart VS Code so the new Path takes effect.'
}
