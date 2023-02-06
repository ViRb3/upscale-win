import sys
import os
from pathlib import Path
from math import ceil

import vapoursynth as vs
from vapoursynth import core

script_dir = Path(__file__).parent.resolve()
sys.path.append(str(script_dir))

os.chdir(script_dir / "runtime" / "vsmlrt")
core.std.LoadPlugin(path="vstrt.dll")
os.chdir(script_dir)

from runtime.vsmlrt.vsmlrt import CUGAN, RIFE, Backend

# settings
core.num_threads = 2
target_width: int = 1920
target_height: int = 1080
target_scale: int = 2
scale_func = core.resize.Lanczos
interpolate_factor: int = 2
backend = Backend.TRT(
    fp16=True,
    output_format=1,  # fp16
    force_fp16=True,
    device_id=0,
    tf32=False,
    use_cudnn=False,
    num_streams=2,
    workspace=None,  # use all VRAM
    use_cuda_graph=True,
)


def eprint(*args, **kwargs):
    """
    print to stderr, needed to view output in vspipe
    """
    print(*args, file=sys.stderr, **kwargs)


def rescale_pad(clip, target_width: int, target_height: int):
    """
    Rescale to target dimensions by padding with black pixels where necessary.
    Transforms non-square pixels to square (1:1 SAR).
    """
    # transform non-square pixels to square
    sar = [props.get(p, 1) for p in ["_SARNum", "_SARDen"]]
    fixed_width = clip.width * max(1, sar[0] / sar[1])
    fixed_height = clip.height * max(1, sar[1] / sar[0])
    # find common factor that will match one dimension and fit the other inside target
    size_factor_w = target_width / fixed_width
    size_factor_h = target_height / fixed_height
    if size_factor_w < size_factor_h:
        size_factor = size_factor_w
        matched_width = True
    else:
        size_factor = size_factor_h
        matched_width = False
    # resize to match first dimension
    clip = scale_func(
        clip,
        fixed_width * size_factor,
        fixed_height * size_factor,
    )
    # pad to match second dimension
    border_l = 0
    border_r = 0
    border_t = 0
    border_b = 0
    if matched_width:
        # https://github.com/vapoursynth/vapoursynth/blob/2ee76bc5163d546e6a296142a6664a29fe7df165/src/core/simplefilters.cpp#L311
        divisor = 1 << clip.format.subsampling_h
        border_count = (target_height - clip.height) // divisor
        border_t = (border_count // 2) * divisor
        border_b = ceil(border_count / 2) * divisor
    else:
        divisor = 1 << clip.format.subsampling_w
        border_count = (target_width - clip.width) // divisor
        border_l = (border_count // 2) * divisor
        border_r = ceil(border_count / 2) * divisor
    clip = core.std.AddBorders(clip, border_l, border_r, border_t, border_b)
    return clip


# load clip
clip = core.ffms2.Source(
    source=dict(globals())["input"],
    cache=False,
)
props = clip.get_frame(0).props

if props.get("_FieldBased", 0) != 0:
    raise Exception("Video is interlaced, deinterlace it first.")

# rescale to optmal dimensions for model
clip = rescale_pad(clip, target_width // target_scale, target_height // target_scale)

if interpolate_factor > 1:
    # skip interpolating on scene change
    clip = core.misc.SCDetect(clip=clip, threshold=0.100)

# default to 1 (BT.709) if prop is None or 2 (undefined)
colorspace = [
    x if x != 2 else 1
    for x in [props.get(p, 2) for p in ["_Matrix", "_Transfer", "_Primaries"]]
]

# models only accept RGB
clip = scale_func(
    clip,
    format=vs.RGBS,
    matrix_in=colorspace[0],
    transfer_in=colorspace[1],
    primaries_in=colorspace[2],
)

# color can exceed 1.0 with CUGAN, causing graphical glitches
clip = core.std.Limiter(clip, max=1.0, planes=[0, 1, 2])

clip = CUGAN(
    clip,
    version=2,
    noise=-1,
    scale=2,
    backend=backend,
)

# if using model over target_scale, downscale
if clip.width % target_width != 0 or clip.height % target_height != 0:
    raise Exception(f"bad clip dimensions")
clip = scale_func(clip, target_width, target_height)

if interpolate_factor > 1:
    # RIFE requires multiples of 32
    th = (clip.height + 31) // 32 * 32
    tw = (clip.width + 31) // 32 * 32
    clip = scale_func(clip, tw, th, src_width=tw, src_height=th)
    clip = RIFE(
        clip,
        multi=interpolate_factor,
        scale=1.0,
        model=46,
        backend=backend,
    )

# convert to YUV420 (BT.709) for h264 encoding
clip = scale_func(
    clip,
    target_width,
    target_height,
    format=vs.YUV420P8,
    matrix=1,
    transfer=1,
    primaries=1,
    src_width=target_width,
    src_height=target_height,
)

clip.set_output()
