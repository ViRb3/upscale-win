# Upscale Win

A workflow for upscaling and interpolating videos with NVIDIA TensorRT acceleration.

## Setup

1. Download and extract all external dependencies:

   | Source                                                       | Files             | Destination                      |
   | ------------------------------------------------------------ | ----------------- | -------------------------------- |
   | [vsmlrt-windows-x64-cuda.v13.7z](https://github.com/AmusementClub/vs-mlrt/releases/download/v13/vsmlrt-windows-x64-cuda.v13.7z) | \*                | .\runtime\vsmlrt\                |
   | [python-3.10.10-embed-amd64.zip](https://www.python.org/ftp/python/3.10.10/python-3.10.10-embed-amd64.zip) | \*                | .\runtime\                       |
   | [VapourSynth64-Portable-R61.7z](https://github.com/vapoursynth/vapoursynth/releases/download/R61/VapourSynth64-Portable-R61.7z) | \*                | .\runtime\                       |
   | [vsutil-0.8.0.zip](https://github.com/Irrational-Encoding-Wizardry/vsutil/archive/refs/tags/0.8.0.zip) | .\vsutil\         | .\runtime\                       |
   | [vivtc-r1.7z](https://github.com/vapoursynth/vivtc/releases/download/R1/vivtc-r1.7z) | .\win64\VIVTC.dll | .\runtime\vapoursynth64\plugins\ |

1. Download and install plugins:

   ```bash
   cd runtime
   .\python.exe .\vsrepo.py -p update
   .\python.exe .\vsrepo.py -p install ffms2 havsfunc akarin
   ```

1. Start upscaling:

   ```powershell
   & .\batch.ps1 "E:\converted\" "E:\Original\*.mp4"
   ```
