import sys
import os
from pathlib import Path
import functools

import vapoursynth as vs
from vapoursynth import core

script_dir = Path(__file__).parent.resolve()
sys.path.append(str(script_dir))

os.chdir(script_dir / "runtime" / "vsmlrt")
core.std.LoadPlugin(path="vstrt.dll")
os.chdir(script_dir)

from runtime.vsmlrt.vsmlrt import CUGAN, RIFE, Backend
from runtime.havsfunc import QTGMC

# =============================================================================
# SETTINGS
# =============================================================================

core.num_threads = 2
# prescale to closest fit within these dimensions, preserving aspect ratio
prescale_w = 960  # None = disable
prescale_h = 540  # None = disable
scale_func = core.resize.Lanczos

colorspace = None  # auto detect
# colorspace = [1, 1, 1]  # HD
# colorspace = [5, 1, 5]  # PAL
# colorspace = [6, 1, 6]  # NTSC

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

deinterlace_mode = None  # True = top field first, False = bottom field first
deinterlace_func = lambda clip: QTGMC(clip, Preset="Slow", FPSDivisor=1)

detelecine_mode = None  # True = top field first, False = bottom field first


def detelecine_func(clip):
    def postprocess(n, f, clip, deinterlaced):
        if f.props["_Combed"] > 0:
            return deinterlaced
        else:
            return clip

    matched_clip = vs.core.vivtc.VFM(clip, 1 if detelecine_mode else 0)
    deinterlaced_clip = QTGMC(matched_clip, TFF=detelecine_mode, FPSDivisor=2)
    clip = vs.core.std.FrameEval(
        matched_clip,
        functools.partial(
            postprocess, clip=matched_clip, deinterlaced=deinterlaced_clip
        ),
        prop_src=matched_clip,
    )
    clip = vs.core.vivtc.VDecimate(clip)
    return clip


upscale_factor: int = 2  # 1 = disable
upscale_func = lambda clip: CUGAN(
    clip,
    version=2,
    noise=-1,
    scale=upscale_factor,
    backend=backend,
)

interpolate_factor: int = 1  # 1 = disable
interpolate_func = lambda clip: RIFE(
    clip,
    multi=interpolate_factor,
    scale=1.0,
    model=46,
    backend=backend,
)

# =============================================================================


def eprint(*args, **kwargs):
    """
    print to stderr, needed to view output in vspipe
    """
    print(*args, file=sys.stderr, **kwargs)


clip = core.ffms2.Source(
    source=dict(globals())["input"],
    cache=False,
)

if deinterlace_mode is not None:
    # do this before getting props so the change is registered
    clip = core.std.SetFieldBased(clip, 2 if deinterlace_mode else 1)

props = clip.get_frame(0).props

if detelecine_mode is not None:
    eprint("Detelecining video")
    clip = scale_func(clip, format=vs.YUV420P8)
    clip = detelecine_func(clip)
elif deinterlace_mode is not None:
    eprint("Deinterlacing video")
    clip = deinterlace_func(clip)
elif props.get("_FieldBased", 0) != 0:
    raise Exception("video is interlaced, but deinterlace_mode is disabled, aborting")

# transform non-square pixels to square
sar = [props.get(p, 1) for p in ["_SARNum", "_SARDen"]]
square_w = clip.width * max(1, sar[0] / sar[1])
square_h = clip.height * max(1, sar[1] / sar[0])

# find common factor that will match one dimension and fit the other inside prescale dimensions
# make sure both dimensions are divisible by their subsampling factor
size_factor_w = prescale_w / square_w if prescale_w is not None else sys.maxsize
size_factor_h = prescale_h / square_h if prescale_h is not None else sys.maxsize
# https://github.com/vapoursynth/vapoursynth/blob/2ee76bc5163d546e6a296142a6664a29fe7df165/src/core/simplefilters.cpp#L311
divisor_w = 1 << clip.format.subsampling_w
divisor_h = 1 << clip.format.subsampling_h
if size_factor_w < size_factor_h:
    temp_w = (square_w * size_factor_w + divisor_w - 1) // divisor_w * divisor_w
    temp_h = (square_h * size_factor_w + divisor_h - 1) // divisor_h * divisor_h
else:
    temp_w = (square_w * size_factor_h + divisor_w - 1) // divisor_w * divisor_w
    temp_h = (square_h * size_factor_h + divisor_h - 1) // divisor_h * divisor_h

clip = scale_func(clip, temp_w, temp_h)

target_w = temp_w * upscale_factor
target_h = temp_h * upscale_factor

if upscale_factor > 1:
    # CUGAN requires multiples of 2
    temp_w = (temp_w + 1) // 2 * 2
    temp_h = (temp_h + 1) // 2 * 2

if interpolate_factor > 1:
    # skip interpolating on scene change
    clip = core.misc.SCDetect(clip=clip, threshold=0.100)

if colorspace is None:
    colorspace = [props.get(p, 2) for p in ["_Matrix", "_Transfer", "_Primaries"]]
    if any(p == 2 for p in colorspace):
        raise Exception("unable to detect colorspace, aborting")

# models only accept RGB, also pad to expected dimensions
clip = scale_func(
    clip,
    temp_w,
    temp_h,
    format=vs.RGBS,
    matrix_in=colorspace[0],
    transfer_in=colorspace[1],
    primaries_in=colorspace[2],
    src_width=temp_w,
    src_height=temp_h,
)

# color can exceed 1.0 with CUGAN, causing graphical glitches
clip = core.std.Limiter(clip, max=1.0, planes=[0, 1, 2])
# clip = core.akarin.Expr(clip, "x 0 1 clamp")

if upscale_factor > 1:
    clip = upscale_func(clip)

if interpolate_factor > 1:
    # RIFE requires multiples of 32
    temp_w = (target_w + 31) // 32 * 32
    temp_h = (target_h + 31) // 32 * 32
    clip = scale_func(clip, temp_w, temp_h, src_width=temp_w, src_height=temp_h)
    clip = interpolate_func(clip)

# convert to YUV420 (BT.709) for h264 encoding
clip = scale_func(
    clip,
    target_w,
    target_h,
    format=vs.YUV420P8,
    matrix=1,
    transfer=1,
    primaries=1,
    src_width=target_w,
    src_height=target_h,
)

clip.set_output()
