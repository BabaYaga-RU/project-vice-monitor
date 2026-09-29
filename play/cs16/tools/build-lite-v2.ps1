[CmdletBinding()]
param(
    [string]$InputZip = (Join-Path $PSScriptRoot '..\user-content\cs16-assets.zip'),
    [string]$OutputZip,
    [string]$VerifiedAccessManifest = (Join-Path $PSScriptRoot 'verified-access-v2.txt'),
    [switch]$NoCompression
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $InputZip -PathType Leaf)) {
    throw "ZIP de assets nao encontrado: $InputZip. Rode tools/prepare-assets.ps1 ou informe -InputZip."
}
if (-not (Test-Path -LiteralPath $VerifiedAccessManifest -PathType Leaf)) {
    throw "Manifesto de acessos nao encontrado: $VerifiedAccessManifest."
}

$InputZip = (Resolve-Path -LiteralPath $InputZip).Path
if (-not $OutputZip) { $OutputZip = Join-Path (Split-Path -Parent $InputZip) 'cs16-lite-v2.zip' }
$outputDirectory = Split-Path -Parent $OutputZip
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
$OutputZip = [IO.Path]::GetFullPath($OutputZip)
if ([string]::Equals($InputZip, $OutputZip, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'O ZIP de saida precisa ser diferente do ZIP de entrada.'
}
if (Test-Path -LiteralPath $OutputZip) {
    throw "A saida ja existe e sera preservada: $OutputZip. Informe outro -OutputZip ou mova essa saida primeiro."
}

$verifiedPaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($line in Get-Content -LiteralPath $VerifiedAccessManifest) {
    $value = $line.Trim()
    if (-not $value -or $value.StartsWith('#')) { continue }
    $value = $value.Replace('\', '/').TrimStart([char[]]@('.', '/'))
    [void]$verifiedPaths.Add($value)
}
if ($verifiedPaths.Count -lt 20 -or -not $verifiedPaths.Contains('cstrike/maps/de_dust2.bsp')) {
    throw 'O manifesto esta vazio/incompleto ou nao contem o BSP de_dust2.'
}
if (-not ($verifiedPaths | Where-Object { $_ -match '^(cstrike|valve)/models/.+\.mdl$' } | Select-Object -First 1)) {
    throw 'O manifesto nao inclui caminhos de modelos; reducao cancelada.'
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$source = [IO.Compression.ZipFile]::OpenRead($InputZip)
$mapEntry = $source.Entries | Where-Object {
    $_.FullName.Replace('\', '/').TrimStart([char[]]@('.', '/')) -ieq 'cstrike/maps/de_dust2.bsp'
} | Select-Object -First 1
if (-not $mapEntry) { $source.Dispose(); throw 'O ZIP nao contem cstrike/maps/de_dust2.bsp.' }

# Obtem os WADs declarados no worldspawn de Dust2; o manifesto registra os demais WADs abertos.
$wadNames = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$mapStream = [IO.MemoryStream]::new()
$mapInput = $mapEntry.Open()
try { $mapInput.CopyTo($mapStream) } finally { $mapInput.Dispose() }
$mapStream.Position = 0
$reader = [IO.BinaryReader]::new($mapStream)
try {
    $version = $reader.ReadInt32()
    if ($version -ne 30) { throw "de_dust2.bsp usa versao BSP $version; esperada GoldSrc BSP30." }
    $entityOffset = 0; $entityLength = 0
    for ($i = 0; $i -lt 15; $i++) {
        $offset = $reader.ReadInt32(); $length = $reader.ReadInt32()
        if ($i -eq 0) { $entityOffset = $offset; $entityLength = $length }
    }
    if ($entityOffset -lt 124 -or $entityLength -le 0 -or $entityLength -gt 16777216) {
        throw 'Lump de entidades BSP invalido.'
    }
    [void]$mapStream.Seek($entityOffset, [IO.SeekOrigin]::Begin)
    $entityText = [Text.Encoding]::ASCII.GetString($reader.ReadBytes($entityLength))
    foreach ($match in [regex]::Matches($entityText, '(?is)"wad"\s*"([^"]*)"')) {
        foreach ($wadPath in ($match.Groups[1].Value -split ';')) {
            $path = $wadPath.Trim().Replace('/', '\')
            if ($path) { [void]$wadNames.Add([IO.Path]::GetFileName($path)) }
        }
    }
} finally { $reader.Dispose(); $mapStream.Dispose() }
if ($wadNames.Count -eq 0) { throw 'Dust2 nao declarou WADs; nao e seguro produzir o Lite v2.' }
Write-Host ('WADs de Dust2: ' + (($wadNames | Sort-Object) -join ', '))

$keep = [Collections.Generic.List[object]]::new()
$removed = @{}
$inputPayload = [long]0
$keptPayload = [long]0
$filesIn = 0
foreach ($entry in $source.Entries) {
    $name = $entry.FullName.Replace('\', '/').TrimStart([char[]]@('.', '/'))
    if (-not $name -or $name.EndsWith('/')) { continue }
    if (-not ($name.StartsWith('cstrike/', [StringComparison]::OrdinalIgnoreCase) -or $name.StartsWith('valve/', [StringComparison]::OrdinalIgnoreCase))) { continue }

    $filesIn++
    $inputPayload += $entry.Length
    $lower = $name.ToLowerInvariant()
    $extension = [IO.Path]::GetExtension($lower)
    $reason = $null

    # First retain the conservative Lite v1 exclusions.
    if ($lower -match '^(cstrike|valve)/sound/') { $reason = 'audio directories' }
    elseif ($extension -in @('.wav','.mp3','.ogg','.opus','.mp2','.mid','.midi','.aif','.aiff','.flac')) { $reason = 'audio files' }
    elseif ($extension -in @('.mp4','.m4v','.mpg','.mpeg','.avi','.wmv','.webm','.mov','.ogv')) { $reason = 'video files' }
    elseif ($lower -match '^(cstrike|valve)/media/') { $reason = 'media' }
    elseif ($lower -match '^(cstrike|valve)/demos/' -or $extension -eq '.dem') { $reason = 'demos' }
    elseif ($lower -match '^cstrike/logos/') { $reason = 'sprays and logos' }
    elseif ($lower -match '^cstrike/downloads/') { $reason = 'download cache' }
    elseif ($lower -match '^cstrike/addons/') { $reason = 'addons and bots' }
    elseif ($lower -match '^valve/maps/') { $reason = 'Half-Life maps' }
    elseif ($lower -match '^valve/overviews/') { $reason = 'Half-Life map overviews' }
    elseif ($lower -match '^valve/resource/(background|logo)' -or $lower -match '^cstrike/resource/background/') { $reason = 'menu/loading backgrounds and logos' }
    elseif ($lower -match '^cstrike/maps/' -and $lower -notmatch '^cstrike/maps/de_dust2\.(bsp|res)$') { $reason = 'other maps and sidecars' }
    elseif ($lower -match '^cstrike/overviews/' -and $lower -notmatch '^cstrike/overviews/(de_dust2\.|maps\.txt$)') { $reason = 'other map overviews' }
    elseif ($extension -in @('.dll','.so','.dylib','.exe','.pdb','.lib')) { $reason = 'native binaries supplied as WebAssembly separately' }

    # WAD retention needs either an explicit BSP declaration or a successful runtime open.
    if (-not $reason -and $extension -eq '.wad' -and
        -not $wadNames.Contains([IO.Path]::GetFileName($name)) -and -not $verifiedPaths.Contains($name)) {
        $reason = 'WADs neither referenced by Dust2 nor opened by Xash'
    }

    # Only prune models proved unopened by the captured Xash filesystem trace.
    # Sprites stay intact until visual weapon/effect firing has been confirmed.
    if (-not $reason -and $extension -eq '.mdl' -and
        $lower -match '^(cstrike|valve)/models/' -and -not $verifiedPaths.Contains($name)) {
        $reason = 'models outside the verified Dust2 runtime trace'
    }

    if ($reason) {
        if (-not $removed.ContainsKey($reason)) { $removed[$reason] = [pscustomobject]@{ Files = 0; Bytes = [long]0 } }
        $removed[$reason].Files++
        $removed[$reason].Bytes += $entry.Length
    } else {
        $keep.Add($entry)
        $keptPayload += $entry.Length
    }
}

$keptNames = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($entry in $keep) { [void]$keptNames.Add($entry.FullName.Replace('\', '/').TrimStart([char[]]@('.', '/'))) }
if (-not $keptNames.Contains('cstrike/maps/de_dust2.bsp')) { $source.Dispose(); throw 'Dust2 foi removido por engano; saida cancelada.' }
foreach ($wadName in $wadNames) {
    if (-not ($keep | Where-Object { $_.FullName -match ('(?i)(^|/)' + [regex]::Escape($wadName) + '$') } | Select-Object -First 1)) {
        $source.Dispose(); throw "WAD declarado ausente na saida: $wadName"
    }
}
foreach ($critical in @('valve/gfx.wad','cstrike/models/v_glock18.mdl','cstrike/sprites/640hud1.spr')) {
    if ($verifiedPaths.Contains($critical) -and -not $keptNames.Contains($critical)) {
        $source.Dispose(); throw "Dependencia observada removida: $critical"
    }
}

$level = if ($NoCompression) { [IO.Compression.CompressionLevel]::NoCompression } else { [IO.Compression.CompressionLevel]::Fastest }
$destination = [IO.Compression.ZipFile]::Open($OutputZip, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($entry in $keep) {
        $newEntry = $destination.CreateEntry($entry.FullName.Replace('\', '/'), $level)
        $input = $entry.Open(); $output = $newEntry.Open()
        try { $input.CopyTo($output) } finally { $output.Dispose(); $input.Dispose() }
    }
} catch {
    $destination.Dispose(); $source.Dispose()
    Remove-Item -LiteralPath $OutputZip -Force -ErrorAction SilentlyContinue
    throw
} finally {
    if ($destination) { $destination.Dispose() }
    if ($source) { $source.Dispose() }
}

$removedFiles = ($removed.Values | Measure-Object Files -Sum).Sum
$removedBytes = ($removed.Values | Measure-Object Bytes -Sum).Sum
Write-Host ''
Write-Host 'REDUCAO CS 1.6 LITE V2'
Write-Host ('Entrada: {0:N0} arquivos; payload {1:N2} MiB; ZIP {2:N2} MiB' -f $filesIn, ($inputPayload / 1MB), ((Get-Item $InputZip).Length / 1MB))
Write-Host ('Lite v2: {0:N0} arquivos; payload {1:N2} MiB; ZIP {2:N2} MiB' -f $keep.Count, ($keptPayload / 1MB), ((Get-Item $OutputZip).Length / 1MB))
Write-Host ('Removidos nesta etapa: {0:N0} arquivos; {1:N2} MiB de payload' -f $removedFiles, ($removedBytes / 1MB))
foreach ($category in ($removed.Keys | Sort-Object)) {
    $item = $removed[$category]
    Write-Host ('  {0}: {1:N0} arquivos; {2:N2} MiB' -f $category, $item.Files, ($item.Bytes / 1MB))
}
Write-Host "ZIP Lite v2: $OutputZip"
Write-Host 'A instalacao original nao foi alterada; sprites, modelos observados e texturas mantidas sem transformacao; engine/WASM permanecem externos.'
