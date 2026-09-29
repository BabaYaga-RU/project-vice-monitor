[CmdletBinding()]
param(
    [string]$InputZip = (Join-Path $PSScriptRoot '..\user-content\cs16-assets.zip'),
    [string]$OutputZip,
    [switch]$NoCompression
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $InputZip -PathType Leaf)) {
    throw "ZIP completo nao encontrado: $InputZip. Gere-o com tools/prepare-assets.ps1."
}
$InputZip = (Resolve-Path -LiteralPath $InputZip).Path
if (-not $OutputZip) { $OutputZip = Join-Path (Split-Path -Parent $InputZip) 'cs16-lite.zip' }
$outputParent = Split-Path -Parent $OutputZip
if (-not (Test-Path $outputParent)) { New-Item -ItemType Directory -Force -Path $outputParent | Out-Null }
$OutputZip = [System.IO.Path]::GetFullPath($OutputZip)
if ([string]::Equals($InputZip, $OutputZip, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'O ZIP de saida precisa ser diferente do ZIP de entrada.'
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$source = [System.IO.Compression.ZipFile]::OpenRead($InputZip)
$mapEntry = $source.Entries | Where-Object { $_.FullName.Replace('\\', '/').TrimStart('./') -ieq 'cstrike/maps/de_dust2.bsp' } | Select-Object -First 1
if (-not $mapEntry) { $source.Dispose(); throw 'O ZIP nao contem cstrike/maps/de_dust2.bsp.' }

# O WAD listado no worldspawn e a dependencia externa declarada pelo proprio BSP.
$wadNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
$entryStream = $mapEntry.Open()
$mapStream = [System.IO.MemoryStream]::new()
$entryStream.CopyTo($mapStream)
$entryStream.Dispose()
$mapStream.Position = 0
$reader = [System.IO.BinaryReader]::new($mapStream)
try {
    $version = $reader.ReadInt32()
    if ($version -ne 30) { throw "de_dust2.bsp usa versao BSP $version; esperada GoldSrc BSP30." }
    $entityOffset = 0; $entityLength = 0
    for ($i = 0; $i -lt 15; $i++) {
        $offset = $reader.ReadInt32(); $length = $reader.ReadInt32()
        if ($i -eq 0) { $entityOffset = $offset; $entityLength = $length }
    }
    if ($entityLength -le 0 -or $entityLength -gt 16777216) { throw 'Lump de entidades BSP invalido.' }
    [void]$mapStream.Seek($entityOffset, [System.IO.SeekOrigin]::Begin)
    $entityText = [System.Text.Encoding]::ASCII.GetString($reader.ReadBytes($entityLength))
    foreach ($wadMatch in [regex]::Matches($entityText, '(?is)"wad"\s*"([^"]*)"')) {
        foreach ($wadPath in ($wadMatch.Groups[1].Value -split ';')) {
            $cleanPath = $wadPath.Trim().Replace('/', '\')
            if ($cleanPath) { [void]$wadNames.Add([System.IO.Path]::GetFileName($cleanPath)) }
        }
    }
} finally { $reader.Dispose(); $mapStream.Dispose() }

if ($wadNames.Count -eq 0) { Write-Warning 'BSP nao declara WAD no worldspawn; por seguranca, todos os WADs de valve/ e cstrike/ serao mantidos.' }
Write-Host ('WADs declarados por de_dust2: ' + $(if ($wadNames.Count) { ($wadNames | Sort-Object) -join ', ' } else { '(nenhum; mantendo todos)' }))

$keep = [System.Collections.Generic.List[object]]::new()
$removed = @{}
$keptPayload = [long]0
$inputPayload = [long]0
$filesIn = 0
foreach ($entry in $source.Entries) {
    $name = $entry.FullName.Replace('\\', '/').TrimStart('./')
    if (-not $name -or $name.EndsWith('/')) { continue }
    if (-not ($name.StartsWith('cstrike/', [System.StringComparison]::OrdinalIgnoreCase) -or $name.StartsWith('valve/', [System.StringComparison]::OrdinalIgnoreCase))) { continue }
    $filesIn++
    $inputPayload += $entry.Length
    $lower = $name.ToLowerInvariant()
    $reason = $null
    if ($lower -match '^(cstrike|valve)/sound/') { $reason = 'audio directories' }
    elseif ([System.IO.Path]::GetExtension($lower) -in @('.wav','.mp3','.ogg','.opus','.mp2','.mid','.midi','.aif','.aiff','.flac')) { $reason = 'audio files' }
    elseif ($lower -match '^(cstrike|valve)/media/') { $reason = 'media' }
    elseif ($lower -match '^(cstrike|valve)/demos/' -or [System.IO.Path]::GetExtension($lower) -eq '.dem') { $reason = 'demos' }
    elseif ($lower -match '^cstrike/logos/') { $reason = 'sprays and logos' }
    elseif ($lower -match '^cstrike/downloads/') { $reason = 'download cache' }
    elseif ($lower -match '^cstrike/addons/') { $reason = 'addons and bots' }
    elseif ($lower -match '^valve/maps/') { $reason = 'Half-Life maps' }
    elseif ($lower -match '^valve/overviews/') { $reason = 'Half-Life map overviews' }
    elseif ($lower -match '^valve/resource/(background|logo)' -or $lower -match '^cstrike/resource/background/') { $reason = 'menu/loading backgrounds and logos' }
    elseif ($lower -match '^cstrike/maps/' -and $lower -notmatch '^cstrike/maps/de_dust2\.(bsp|res)$') { $reason = 'other maps and map sidecars' }
    elseif ($lower -match '^cstrike/overviews/' -and $lower -notmatch '^cstrike/overviews/(de_dust2\.|maps\.txt$)') { $reason = 'other map overviews' }
    elseif ([System.IO.Path]::GetExtension($lower) -in @('.dll','.so','.dylib','.exe','.pdb','.lib')) { $reason = 'native platform binaries (WASM modules are supplied by the web client)' }
    elseif ([System.IO.Path]::GetExtension($lower) -eq '.wad' -and $wadNames.Count -gt 0 -and [System.IO.Path]::GetFileName($name) -ine 'gfx.wad' -and -not $wadNames.Contains([System.IO.Path]::GetFileName($name))) { $reason = 'WAD not declared by de_dust2 or engine base' }

    if ($reason) {
        if (-not $removed.ContainsKey($reason)) { $removed[$reason] = [pscustomobject]@{ Files = 0; Bytes = [long]0 } }
        $removed[$reason].Files++
        $removed[$reason].Bytes += $entry.Length
    } else {
        $keep.Add($entry)
        $keptPayload += $entry.Length
    }
}
if (-not $keep.Where({ $_.FullName.Replace('\\','/').TrimStart('./') -ieq 'cstrike/maps/de_dust2.bsp' }).Count) {
    $source.Dispose(); throw 'Regra interna removeu o mapa requerido; saida cancelada.'
}

if (Test-Path -LiteralPath $OutputZip) { Remove-Item -LiteralPath $OutputZip -Force }
$level = if ($NoCompression) { [System.IO.Compression.CompressionLevel]::NoCompression } else { [System.IO.Compression.CompressionLevel]::Fastest }
$destination = [System.IO.Compression.ZipFile]::Open($OutputZip, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($entry in $keep) {
        $newEntry = $destination.CreateEntry($entry.FullName.Replace('\\', '/'), $level)
        $input = $entry.Open(); $output = $newEntry.Open()
        try { $input.CopyTo($output) } finally { $output.Dispose(); $input.Dispose() }
    }
} finally { $destination.Dispose(); $source.Dispose() }

$keptFiles = $keep.Count
$removedFiles = ($removed.Values | Measure-Object Files -Sum).Sum
$removedBytes = ($removed.Values | Measure-Object Bytes -Sum).Sum
Write-Host ''
Write-Host 'REDUCAO CS 1.6 LITE'
Write-Host ('Arquivos originais: {0:N0}; payload: {1:N2} MiB; ZIP: {2:N2} MiB' -f $filesIn, ($inputPayload / 1MB), ((Get-Item $InputZip).Length / 1MB))
Write-Host ('Arquivos Lite: {0:N0}; payload preservado: {1:N2} MiB; ZIP: {2:N2} MiB' -f $keptFiles, ($keptPayload / 1MB), ((Get-Item $OutputZip).Length / 1MB))
Write-Host ('Removidos: {0:N0} arquivos, {1:N2} MiB de payload' -f $removedFiles, ($removedBytes / 1MB))
foreach ($reason in ($removed.Keys | Sort-Object)) {
    $item = $removed[$reason]
    Write-Host ('  {0}: {1:N0} arquivos, {2:N2} MiB' -f $reason, $item.Files, ($item.Bytes / 1MB))
}
Write-Host "ZIP Lite: $OutputZip"
Write-Host 'Texturas nao foram alteradas; WASM/engine nao entram no ZIP.'
