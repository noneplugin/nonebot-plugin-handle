import random
from io import BytesIO
from pathlib import Path
from typing import List, Tuple
from pypinyin import pinyin, Style
from PIL import ImageFont
from PIL.Image import Image as IMG
from PIL.ImageFont import FreeTypeFont

resource_dir = Path(__file__).parent / "resources"
fonts_dir = resource_dir / "fonts"
data_dir = resource_dir / "data"
idiom_path = data_dir / "idioms.txt"


def random_idiom() -> str:
    with idiom_path.open("r", encoding="utf-8") as f:
        return random.choice(f.readlines()).strip()


# fmt: off
# 声母
INITIALS = ["zh", "z", "y", "x", "w", "t", "sh", "s", "r", "q", "p", "n", "m", "l", "k", "j", "h", "g", "f", "d", "ch", "c", "b"]
# 韵母
FINALS = [
    "ün", "üe", "üan", "ü", "uo", "un", "ui", "uang", "uan", "uai", "ua", "ou", "ong", "iu", "iong", "io", "ing",
    "in", "ie", "iao", "iang", "ian", "ia", "er", "eng", "en", "ei", "ao", "ang", "an", "ai", "u", "o", "i", "e", "a"
]
# fmt: on


def get_pinyin(idiom: str) -> List[Tuple[str, str, str]]:
    pys = pinyin(idiom, style=Style.TONE3, v_to_u=True)
    results = []
    for p in pys:
        py = p[0]
        if py[-1].isdigit():
            tone = py[-1]
            py = py[:-1]
        else:
            tone = ""
        initial = ""
        for i in INITIALS:
            if py.startswith(i):
                initial = i
                break
        final = ""
        for f in FINALS:
            if py.endswith(f):
                final = f
                break
        results.append((initial, final, tone))  # 声母，韵母，声调
    return results


def save_jpg(frame: IMG) -> BytesIO:
    output = BytesIO()
    frame = frame.convert("RGB")
    frame.save(output, format="jpeg")
    return output


def load_font(name: str, fontsize: int) -> FreeTypeFont:
    return ImageFont.truetype(str(fonts_dir / name), fontsize, encoding="utf-8")
