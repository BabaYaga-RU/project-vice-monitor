param([string]$GameFiles)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$OutputDir = Join-Path $Root 'user-content'
$InstallDir = Join-Path $OutputDir 'game'
$ZipPath = Join-Path $OutputDir 'cs16-assets.zip'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if (-not $GameFiles) {
    $steamRoots = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Steam'),
        (Join-Path $env:ProgramFiles 'Steam'),
        (Join-Path $env:LOCALAPPDATA 'Steam')
    ) | Where-Object { $_ -and (Test-Path $_) }
    $libraries = [System.Collections.Generic.List[string]]::new()
    foreach ($steamRoot in $steamRoots) {
        $libraries.Add($steamRoot)
        $libraryFile = Join-Path $steamRoot 'steamapps\libraryfolders.vdf'
        if (Test-Path $libraryFile) {
            $vdf = Get-Content -Raw $libraryFile
            foreach ($match in [regex]::Matches($vdf, '"path"\s+"([^"]+)"')) {
                $libraries.Add($match.Groups[1].Value.Replace('\\', '\'))
            }
        }
    }
    $candidates = foreach ($library in ($libraries | Select-Object -Unique)) {
        Join-Path $library 'steamapps\common\Half-Life'
        Join-Path $library 'steamapps\common\Counter-Strike'
    }
    $GameFiles = $candidates | Where-Object {
        (Test-Path (Join-Path $_ 'cstrike')) -and (Test-Path (Join-Path $_ 'valve'))
    } | Select-Object -First 1
    if (-not $GameFiles) {
        throw 'Instalação não encontrada automaticamente. Passe -GameFiles com a pasta que contém cstrike e valve.'
    }
}

$source = (Resolve-Path -LiteralPath $GameFiles).Path
foreach ($folder in @('cstrike', 'valve')) {
    if (-not (Test-Path (Join-Path $source $folder))) { throw "Pasta $folder não encontrada em $source" }
}
$sourceMap = Join-Path $source 'cstrike\maps\de_dust2.bsp'
if (-not (Test-Path $sourceMap)) { throw "de_dust2.bsp não encontrado em $sourceMap" }
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
if (-not [string]::Equals($source, $InstallDir, [System.StringComparison]::OrdinalIgnoreCase)) {
    foreach ($folder in @('valve', 'cstrike')) {
        $target = Join-Path $InstallDir $folder
        if (Test-Path $target) { Remove-Item -LiteralPath $target -Recurse -Force }
        Copy-Item -LiteralPath (Join-Path $source $folder) -Destination $InstallDir -Recurse
    }
}

$map = Join-Path $InstallDir 'cstrike\maps\de_dust2.bsp'
if (-not (Test-Path $map)) { throw "de_dust2.bsp não encontrado em $map" }
if (Test-Path $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$archive = [System.IO.Compression.ZipFile]::Open($ZipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($folder in @('valve', 'cstrike')) {
        Get-ChildItem -LiteralPath (Join-Path $InstallDir $folder) -File -Recurse | ForEach-Object {
            $relative = $_.FullName.Substring($InstallDir.Length + 1).Replace('\', '/')
            $entry = $archive.CreateEntry($relative, [System.IO.Compression.CompressionLevel]::NoCompression)
            $inputStream = [System.IO.File]::OpenRead($_.FullName)
            $outputStream = $entry.Open()
            try { $inputStream.CopyTo($outputStream) }
            finally { $outputStream.Dispose(); $inputStream.Dispose() }
        }
    }
} finally { $archive.Dispose() }
Write-Host "Assets copiados sem modificar a fonte: $source"
Write-Host "ZIP preparado: $ZipPath"
Write-Host ('Tamanho: {0:N1} MiB' -f ((Get-Item $ZipPath).Length / 1MB))
Write-Host 'Não distribua nem publique esse ZIP; selecione-o no navegador.'
