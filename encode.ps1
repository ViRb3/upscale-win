param (
    [Parameter(Mandatory = $true)][string]$dest_dir,
    [Parameter(Mandatory = $true)][string]$source_glob
)
$ErrorActionPreference = "Stop"

Write-Output "Started encode loop..."

while ($true) {
    foreach ($source in Get-Item $source_glob | Sort-Object) {
        $temp = Join-Path $dest_dir ($source.BaseName + "-x264.tmp")
        $encoded = Join-Path $dest_dir ($source.BaseName + "-x264.mp4")
    
        if (Test-Path -LiteralPath $encoded -PathType Leaf) {
            continue
        }
    
        Write-Output "Encoding $source"
    
        & .\runtime\HandBrakeCLI -i "$source" -o "$temp" --preset-import-file "x264.json" --preset "x264"
        if (! $?) {
            exit 1
        }
    
        Move-Item -LiteralPath "$temp" -Destination "$encoded"
    }
    Start-Sleep 60
}
