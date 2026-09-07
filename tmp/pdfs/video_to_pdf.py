import argparse
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from reportlab.lib.pagesizes import portrait
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def ffprobe_json(ffprobe: Path, video: Path) -> str:
    return subprocess.check_output(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,duration,nb_frames",
            "-of",
            "default=noprint_wrappers=1",
            str(video),
        ],
        text=True,
        stderr=subprocess.STDOUT,
    )


def parse_probe(output: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def frame_similarity(a: Path, b: Path) -> float:
    with Image.open(a).convert("RGB") as img_a, Image.open(b).convert("RGB") as img_b:
        img_a.thumbnail((160, 160))
        img_b.thumbnail((160, 160))
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size)
        diff = ImageChops.difference(img_a, img_b)
        stat = ImageStat.Stat(diff)
        rms = math.sqrt(sum(value * value for value in stat.rms) / len(stat.rms))
        return rms


def run_ffmpeg(ffmpeg: Path, video: Path, frames_dir: Path, fps: float) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = frames_dir / "frame_%04d.jpg"
    subprocess.check_call(
        [
            str(ffmpeg),
            "-y",
            "-i",
            str(video),
            "-vf",
            f"fps={fps},scale=1080:-2",
            "-q:v",
            "3",
            str(pattern),
        ]
    )
    return sorted(frames_dir.glob("frame_*.jpg"))


def keep_distinct_frames(frames: list[Path], max_pages: int) -> list[Path]:
    if not frames:
        return []

    distinct = [frames[0]]
    last = frames[0]
    for frame in frames[1:]:
        if frame_similarity(last, frame) >= 8:
            distinct.append(frame)
            last = frame

    if len(distinct) <= max_pages:
        return distinct

    step = (len(distinct) - 1) / (max_pages - 1)
    chosen = []
    for index in range(max_pages):
        chosen.append(distinct[round(index * step)])
    return chosen


def write_pdf(frames: list[Path], output: Path) -> None:
    if not frames:
        raise RuntimeError("No frames were extracted from the video.")

    output.parent.mkdir(parents=True, exist_ok=True)
    first = Image.open(frames[0])
    page_size = portrait((first.width, first.height))
    first.close()

    pdf = canvas.Canvas(str(output), pagesize=page_size)
    page_w, page_h = page_size
    for frame in frames:
        with Image.open(frame) as image:
            image = image.convert("RGB")
            img_w, img_h = image.size
            scale = min(page_w / img_w, page_h / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
            x = (page_w - draw_w) / 2
            y = (page_h - draw_h) / 2
            pdf.drawImage(ImageReader(image), x, y, width=draw_w, height=draw_h)
        pdf.showPage()
    pdf.save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--ffprobe", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fps", type=float, default=0.33)
    parser.add_argument("--max-pages", type=int, default=36)
    args = parser.parse_args()

    ffmpeg = Path(args.ffmpeg)
    ffprobe = Path(args.ffprobe)
    video = Path(args.video)
    frames_dir = Path(args.frames_dir)
    output = Path(args.output)

    probe = parse_probe(ffprobe_json(ffprobe, video))
    frames = run_ffmpeg(ffmpeg, video, frames_dir, args.fps)
    selected = keep_distinct_frames(frames, args.max_pages)
    write_pdf(selected, output)

    print(f"video={video}")
    print(f"source={probe}")
    print(f"extracted_frames={len(frames)}")
    print(f"pdf_pages={len(selected)}")
    print(f"output={output}")


if __name__ == "__main__":
    main()
