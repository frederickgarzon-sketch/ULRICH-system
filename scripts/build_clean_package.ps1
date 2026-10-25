param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $OutputPath) {
    $OutputPath = Join-Path (Split-Path $workspace -Parent) "Behavior-Monitor-Research-Console-CLEAN.zip"
}
$output = [IO.Path]::GetFullPath($OutputPath)

if (Test-Path -LiteralPath $output) { Remove-Item -LiteralPath $output -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::Open($output, [IO.Compression.ZipArchiveMode]::Create)
try {
    Get-ChildItem -LiteralPath $workspace -File -Recurse -Force | ForEach-Object {
        $relative = $_.FullName.Substring($workspace.Length + 1)
        $parts = $relative -split "[\\/]"
        $excluded = ([IO.Path]::GetFullPath($_.FullName) -eq $output) -or
                    ($parts -contains ".venv") -or
                    ($parts -contains ".git") -or
                    ($parts -contains "__pycache__") -or
                    ($parts -contains ".pytest_cache") -or
                    ($parts[0] -eq "logs") -or
                    ($relative -eq ".env") -or
                    ($relative -eq ".env.backup") -or
                    ($relative -match "^data[\\/].*\.(db|sqlite)(-shm|-wal)?$") -or
                    ($relative -eq "data\research_reference_features.csv") -or
                    ($relative -eq "data\research_reference_metadata.json") -or
                    ($relative -match "\.py[co]$")
        if (-not $excluded) {
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $_.FullName, $relative, [IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    }
}
finally {
    $archive.Dispose()
}

Write-Output $output
