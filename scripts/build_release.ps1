param(
    [string]$Version = "",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuildDir = Join-Path $RepoRoot "build"
$DistDir = Join-Path $RepoRoot "dist"
$ReleaseDir = Join-Path $RepoRoot "release_artifacts"
$InstallerScript = Join-Path $RepoRoot "installer\StankyTools.nsi"
$SpecFile = Join-Path $RepoRoot "StankyTools.spec"
$MainFile = Join-Path $RepoRoot "main.py"

function Get-StankyRelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    $baseUri = [Uri]$baseFull
    $targetUri = [Uri]$targetFull
    return [Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace(
        '/',
        [System.IO.Path]::DirectorySeparatorChar
    )
}
Set-Location $RepoRoot
if ([string]::IsNullOrWhiteSpace($Version)) {
    if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_REF_NAME)) {
        $Version = $env:GITHUB_REF_NAME
    }
    else {
        $Version = "dev"
    }
}

$Version = $Version.Trim()
if ($Version.StartsWith("v")) {
    $Version = $Version.Substring(1)
}

Write-Host "Repository: $RepoRoot"
Write-Host "Version: $Version"
Write-Host "Dist folder: $DistDir"
Write-Host "Release folder: $ReleaseDir"

foreach ($Path in @($BuildDir, $DistDir, $ReleaseDir)) {
    if (Test-Path $Path) {
        Remove-Item $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

if (Test-Path $SpecFile) {
    Write-Host "Building from StankyTools.spec..."
    python -m PyInstaller `
        --clean `
        --noconfirm `
        --distpath $DistDir `
        --workpath $BuildDir `
        $SpecFile
}
elseif (Test-Path $MainFile) {
    Write-Host "No spec file found. Building from main.py..."
    python -m PyInstaller `
        --clean `
        --noconfirm `
        --onedir `
        --windowed `
        --name "StankyTools" `
        --distpath $DistDir `
        --workpath $BuildDir `
        $MainFile
}
else {
    throw "Neither StankyTools.spec nor main.py was found."
}

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$AppExe = Get-ChildItem -Path $DistDir -Filter "StankyTools.exe" -File -Recurse | Select-Object -First 1
if (-not $AppExe) {
    Write-Host "Contents of dist:"
    Get-ChildItem -Path $DistDir -Recurse | ForEach-Object { Write-Host $_.FullName }
    throw "StankyTools.exe was not found anywhere under $DistDir."
}

$AppDir = Split-Path -Parent $AppExe.FullName
$ExeRelativePath = Get-StankyRelativePath -BasePath $DistDir -TargetPath $AppExe.FullName
$InternalDir = Join-Path $AppDir "_internal"
$PythonDllItem = Get-ChildItem -LiteralPath $InternalDir -Filter "python*.dll" -File | Where-Object {
    $_.Name -match '^python\d+\.dll$'
} | Select-Object -First 1
$PythonDll = if ($PythonDllItem) { $PythonDllItem.FullName } else { Join-Path $InternalDir "python*.dll" }
$PySideDir = Join-Path $InternalDir "PySide6"
$AssetsDir = Join-Path $InternalDir "assets"
$CatalogDb = Join-Path $AssetsDir "catalog\catalog.sqlite3"

$RequiredPaths = @(
    @{ Label = "StankyTools.exe"; Path = $AppExe.FullName },
    @{ Label = "_internal"; Path = $InternalDir },
    @{ Label = "Python runtime DLL"; Path = $PythonDll },
    @{ Label = "PySide6"; Path = $PySideDir },
    @{ Label = "assets"; Path = $AssetsDir },
    @{ Label = "catalog database"; Path = $CatalogDb }
)

foreach ($Required in $RequiredPaths) {
    if (-not (Test-Path -LiteralPath $Required.Path)) {
        Write-Host "Contents of dist before failure:"
        Get-ChildItem -Path $DistDir -Recurse | ForEach-Object { Write-Host $_.FullName }
        throw "Required release runtime item missing: $($Required.Label) at $($Required.Path)"
    }
}

function Optimize-PySidePlugins {
    param([Parameter(Mandatory = $true)][string]$PySideRoot)

    if (-not (Test-Path -LiteralPath $PySideRoot)) {
        return
    }

    $PluginRoot = Join-Path $PySideRoot "Qt6\plugins"
    if (-not (Test-Path -LiteralPath $PluginRoot)) {
        $PluginRoot = Join-Path $PySideRoot "plugins"
    }
    if (-not (Test-Path -LiteralPath $PluginRoot)) {
        return
    }

    $KeepPluginDirs = @("platforms", "imageformats", "styles")
    Get-ChildItem -LiteralPath $PluginRoot -Directory | Where-Object {
        $KeepPluginDirs -notcontains $_.Name
    } | ForEach-Object {
        Write-Host "Removing unused Qt plugin folder: $($_.FullName)"
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }

    $Platforms = Join-Path $PluginRoot "platforms"
    if (Test-Path -LiteralPath $Platforms) {
        Get-ChildItem -LiteralPath $Platforms -File | Where-Object {
            $_.Name -ne "qwindows.dll"
        } | ForEach-Object {
            Write-Host "Removing unused Qt platform plugin: $($_.Name)"
            Remove-Item -LiteralPath $_.FullName -Force
        }
    }

    $ImageFormats = Join-Path $PluginRoot "imageformats"
    if (Test-Path -LiteralPath $ImageFormats) {
        $KeepImageFormats = @("qgif.dll", "qico.dll", "qjpeg.dll", "qsvg.dll", "qwebp.dll")
        Get-ChildItem -LiteralPath $ImageFormats -File | Where-Object {
            $KeepImageFormats -notcontains $_.Name
        } | ForEach-Object {
            Write-Host "Removing unused Qt image plugin: $($_.Name)"
            Remove-Item -LiteralPath $_.FullName -Force
        }
    }

    $RemoveQtBinaries = @(
        "Qt6Pdf.dll", "Qt6PdfWidgets.dll", "QtPdf.pyd", "QtPdfWidgets.pyd",
        "Qt6Quick.dll", "Qt6QuickControls2.dll", "Qt6QuickTemplates2.dll", "QtQuick.pyd", "QtQuickControls2.pyd", "QtQuickWidgets.pyd",
        "Qt6Qml.dll", "Qt6QmlMeta.dll", "Qt6QmlModels.dll", "Qt6QmlWorkerScript.dll", "QtQml.pyd",
        "Qt6WebEngineCore.dll", "Qt6WebEngineQuick.dll", "QtWebEngineCore.pyd", "QtWebEngineWidgets.pyd",
        "Qt6Multimedia.dll", "Qt6MultimediaWidgets.dll", "QtMultimedia.pyd", "QtMultimediaWidgets.pyd", "opengl32sw.dll"
    )
    Get-ChildItem -LiteralPath $PySideRoot -Recurse -File | Where-Object {
        $RemoveQtBinaries -contains $_.Name
    } | ForEach-Object {
        Write-Host "Removing unused Qt binary: $($_.Name)"
        Remove-Item -LiteralPath $_.FullName -Force
    }

    foreach ($OptionalDirName in @("qml", "translations")) {
        $OptionalDir = Join-Path $PySideRoot $OptionalDirName
        if (Test-Path -LiteralPath $OptionalDir) {
            Write-Host "Removing unused PySide6 folder: $OptionalDir"
            Remove-Item -LiteralPath $OptionalDir -Recurse -Force
        }
    }
}

Optimize-PySidePlugins -PySideRoot $PySideDir

Write-Host "Application executable: $($AppExe.FullName)"
Write-Host "Relative executable path: $ExeRelativePath"
Write-Host "Verified onedir runtime structure:"
foreach ($Required in $RequiredPaths) {
    Write-Host " - $($Required.Label): $($Required.Path)"
}

$PortableName = "StankyTools-Portable-v$Version.zip"
$PortablePath = Join-Path $ReleaseDir $PortableName
if (Test-Path $PortablePath) {
    Remove-Item $PortablePath -Force
}

# Portable releases must contain the full StankyTools folder, not only its contents.
Compress-Archive `
    -Path $AppDir `
    -DestinationPath $PortablePath `
    -CompressionLevel Optimal `
    -Force

Write-Host "Portable ZIP created: $PortablePath"

if (-not $SkipInstaller) {
    if (-not (Test-Path $InstallerScript)) {
        throw "NSIS script was not found: $InstallerScript"
    }

    $MakeNsisCandidates = @(
        (Get-Command "makensis.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        "C:\Program Files (x86)\NSIS\makensis.exe",
        "C:\Program Files\NSIS\makensis.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }

    $MakeNsis = $MakeNsisCandidates | Select-Object -First 1
    if (-not $MakeNsis) {
        throw "NSIS makensis.exe was not found. Install NSIS or run with -SkipInstaller."
    }

    Write-Host "Using NSIS: $MakeNsis"
    & $MakeNsis `
        "/DAPP_VERSION=$Version" `
        "/DDIST_DIR=$DistDir" `
        "/DOUTPUT_DIR=$ReleaseDir" `
        "/DAPP_EXE_REL=$ExeRelativePath" `
        $InstallerScript

    if ($LASTEXITCODE -ne 0) {
        throw "NSIS failed with exit code $LASTEXITCODE."
    }
}

Write-Host ""
Write-Host "Release artifacts created in $ReleaseDir"
Get-ChildItem -Path $ReleaseDir -File | ForEach-Object {
    Write-Host " - $($_.Name) [$([math]::Round($_.Length / 1MB, 2)) MB]"
}
