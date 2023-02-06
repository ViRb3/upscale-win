param (
    [Parameter(Mandatory = $true)][string]$dest_dir,
    [Parameter(Mandatory = $true)][string]$source_glob
)
$ErrorActionPreference = "Stop"

foreach ($source in Get-Item $source_glob | Sort-Object) {
    $temp = Join-Path $dest_dir ($source.BaseName + ".tmp")
    $raw = Join-Path $dest_dir ($source.BaseName + "-UPHD.mp4")

    if (Test-Path -LiteralPath $raw -PathType Leaf) {
        Write-Output "Already exists $source"
        continue
    }

    Write-Output "Upscaling $source"

    $env:infer_vspipe = "runtime\vspipe --arg input=`"$source`" -c y4m `"inference.py`" -"
    $env:infer_ffmpeg = @("ffmpeg", 
        "-i - -i `"$source`"", 
        "-map 0:v -map 1:a -map 1:s?", 
        "-c:a copy -c:s mov_text -c:v h264_nvenc", 
        "-max_interleave_delta 0 -rc:v vbr -cq:v 5 -pix_fmt yuv420p", 
        "-hide_banner -loglevel warning -stats -y -f mp4 `"$temp`"") -join " "
   
    $env:CUDA_MODULE_LOADING = "LAZY"
    cmd /s /c --% "%infer_vspipe% | %infer_ffmpeg%"
    if (! $?) {
        exit 1
    }

    Move-Item -LiteralPath "$temp" -Destination "$raw"
}
