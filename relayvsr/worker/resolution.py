"""CPU-only source inspection and fixed Full HD output geometry."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import os


class AlreadyFullHD(Exception):
    def __init__(self, width, height):
        self.width, self.height = width, height
        super().__init__(f"Исходник {width}×{height} уже достигает размера Full HD")


@dataclass(frozen=True)
class FrameSize:
    width: int
    height: int

    @property
    def output(self):
        return self.width * 4, self.height * 4


def model_size(width: int, height: int, sample_aspect_ratio=1) -> FrameSize:
    if width <= 0 or height <= 0:
        raise ValueError("Некорректный размер исходника")
    aspect = Fraction(sample_aspect_ratio or 1)
    if aspect <= 0:
        aspect = Fraction(1)
    display_width = width * aspect
    if display_width >= 1920 or height >= 1080:
        raise AlreadyFullHD(round(display_width), height)
    scale = min(Fraction(480, 1) / display_width, Fraction(270, height))
    return FrameSize(max(1, round(display_width * scale)), max(1, round(height * scale)))


def source_address(source):
    return source.get("url") or str(Path(os.environ.get("RELAYVSR_INPUT", "/input")) / source["file"])


def source_options(source):
    headers = "".join(f"{k}: {v}\r\n" for k, v in source.get("headers", {}).items())
    return {"headers": headers} if headers else {}


def inspect_source(source):
    # Opening the container reads metadata, without decoding frames or importing torch.
    import av
    with av.open(source_address(source), options=source_options(source), timeout=(5, 10)) as media:
        if not media.streams.video:
            raise ValueError("В источнике нет видео")
        video = media.streams.video[0]
        return model_size(video.width, video.height, video.sample_aspect_ratio)
