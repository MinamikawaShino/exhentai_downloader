import os
from datetime import datetime
from pathlib import Path

from PIL import Image

from .utils import resolve_long_path, restore_timestamps


def _convert_pil(src: str, dst: str, white_bg: bool) -> tuple[bool, str]:
    try:
        with Image.open(src) as img:
            img.load()
            if white_bg and (
                img.mode in ("RGBA", "LA")
                or (img.mode == "P" and "transparency" in img.info)
            ):
                img = img.convert("RGBA")
                bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                bg.paste(img, (0, 0), img)
                img = bg.convert("RGB")
            img.save(dst, format="PNG", optimize=False)
        return True, "Pillow"
    except Exception as e:
        return False, str(e)


def _convert_ffmpeg(src: str, dst: str, white_bg: bool) -> tuple[bool, str]:
    import subprocess

    try:
        if white_bg:
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-err_detect", "ignore_err", "-i", src,
                "-f", "lavfi", "-i", "color=white:s=16x16",
                "-filter_complex",
                "[1:v][0:v]scale2ref[bg][fg];[bg][fg]overlay=format=auto:shortest=1",
                dst,
            ]
        else:
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-err_detect", "ignore_err", "-i", src, dst,
            ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0:
            return True, "FFmpeg"
        return False, res.stderr.decode("utf-8", errors="ignore")
    except FileNotFoundError:
        return False, "ffmpeg not found"
    except Exception as e:
        return False, str(e)


def _convert_magick(src: str, dst: str, white_bg: bool) -> tuple[bool, str]:
    import subprocess

    try:
        cmd = ["magick", src]
        if white_bg:
            cmd.extend(["-background", "white", "-alpha", "remove", "-alpha", "off"])
        cmd.extend(["-quality", "100", dst])
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0:
            return True, "ImageMagick"
        return False, res.stderr.decode("utf-8", errors="ignore")
    except FileNotFoundError:
        return False, "magick not found"
    except Exception as e:
        return False, str(e)


def _convert_dwebp(src: str, dst: str) -> tuple[bool, str]:
    import subprocess

    try:
        cmd = ["dwebp", src, "-o", dst, "-quiet"]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0:
            return True, "dwebp"
        return False, res.stderr.decode("utf-8", errors="ignore")
    except FileNotFoundError:
        return False, "dwebp not found"
    except Exception as e:
        return False, str(e)


def convert_webp_to_png(
    src_path: Path, white_bg: bool
) -> tuple[bool, str, str]:
    src_str = str(src_path)
    dst_str = str(src_path.with_suffix(".png"))
    src_long = resolve_long_path(src_str)
    dst_long = resolve_long_path(dst_str)

    dst_path = Path(dst_str)

    if dst_path.exists():
        try:
            src_path.unlink()
            return True, "DeleteWebP_AlreadyHadPNG", ""
        except Exception as e:
            return False, "DeleteWebP_AlreadyHadPNG", str(e)

    try:
        stat = src_path.stat()
        c_time, m_time, a_time = stat.st_ctime, stat.st_mtime, stat.st_atime
    except Exception:
        c_time = m_time = a_time = datetime.now().timestamp()

    engines = [
        lambda: _convert_pil(src_long, dst_long, white_bg),
        lambda: _convert_ffmpeg(src_long, dst_long, white_bg),
        lambda: _convert_magick(src_long, dst_long, white_bg),
        lambda: _convert_dwebp(src_long, dst_long),
    ]

    for converter in engines:
        success, engine_name = converter()
        if success:
            restore_timestamps(dst_long, c_time, a_time, m_time)
            try:
                os.remove(src_long)
            except Exception:
                pass
            return True, engine_name, ""

    if os.path.exists(dst_long):
        try:
            os.remove(dst_long)
        except Exception:
            pass

    return False, "", "All conversion engines failed"