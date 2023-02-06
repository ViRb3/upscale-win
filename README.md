# Upscale Win

A workflow for upscaling and interpolating videos with NVIDIA TensorRT acceleration.

## Setup

1. Download and extract all dependencies:

   | Source                                                                                                                              | Files                         | Destination                      |
   | ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | -------------------------------- |
   | [vsmlrt-windows-x64-cuda.v13.7z](https://github.com/AmusementClub/vs-mlrt/releases/download/v13/vsmlrt-windows-x64-cuda.v13.7z)     | \*                            | ./runtime/vsmlrt/                |
   | [python-3.11.1-embed-amd64.zip](https://www.python.org/ftp/python/3.11.1/python-3.11.1-embed-amd64.zip)                             | \*                            | ./runtime/                       |
   | [vapoursynth-classic-R57.A6-x64.zip](https://github.com/AmusementClub/vapoursynth-classic/releases/download/R57.A6/release-x64.zip) | \*                            | ./runtime/                       |
   | [ffms2-2.40-msvc.7z](https://github.com/FFMS/ffms2/releases/download/2.40/ffms2-2.40-msvc.7z)                                       | ffms2-2.40-msvc/x64/ffms2.dll | ./runtime/vapoursynth64/plugins/ |

1. Start upscaling:

   ```powershell
   & .\batch.ps1 "E:\converted\" "E:\Original\*.mp4"
   ```
