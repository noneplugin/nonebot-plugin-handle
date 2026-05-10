import json
import random
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple, TypedDict, Optional

from PIL import ImageFont
from PIL.Image import Image as IMG
from PIL.ImageFont import FreeTypeFont
from pypinyin import Style, pinyin as py_get_pinyin

resource_dir = Path(__file__).parent / "resources"
fonts_dir = resource_dir / "fonts"
data_dir = resource_dir / "data"
handle_common_idiom_path = data_dir / "common_idioms.json"
handle_all_idiom_path = data_dir / "idioms.json"
handle_answer_path = data_dir / "answers.json"


class IdiomEntry(TypedDict):
    """
    成语答案类型
    """
    explanation: str
    pinyin: List[str]


HANDLE_COMMON_PHRASES: List[str] = json.load(
    handle_common_idiom_path.open("r", encoding="utf-8")
)
HANDLE_LEGAL_PHRASES: List[str] = json.load(
    handle_all_idiom_path.open("r", encoding="utf-8")
)
HANDLE_ANSWER_PHRASES: Dict[str, IdiomEntry] = json.load(
    handle_answer_path.open("r", encoding="utf-8")
)


def v_to_u(v_strings: List[str]) -> List[str]:
    """
    将韵母的v转为ü
    """

    return [v_str.replace("v", "ü") for v_str in v_strings]


def wordbase_updater(
    idiom: str,
    explanation: Optional[str] = None,
    pinyin: Optional[List[str]] = None,
    hard: Optional[bool] = None,
) -> Tuple[bool, str, List[str]]:
    """
    idiom: 需要更新或新增的成语词条
    explanation: 词条的释义，若 `None` 且在词库中不存在，则默认为“未提供该成语的解释说明”
    pinyin: 词条的拼音，若 `None` 则默认求出拼音
    hard: 是否为难词，若 `None` 则不对难易词库修改

    return: 是否为新增成语，成语释义，词条的拼音
    """
    if (not idiom) or (len(idiom) != 4):
        raise ValueError("不可以非四字成语载入词库")

    if (existance := (idiom in HANDLE_LEGAL_PHRASES)) and (explanation is None):
        # 这个判断的顺序必须高于下面的判断语句
        explanation = HANDLE_ANSWER_PHRASES[idiom]["explanation"]

    if explanation is None:
        explanation = "未提供该成语的解释说明"

    if not existance:
        HANDLE_LEGAL_PHRASES.append(idiom)
        json.dump(
            HANDLE_LEGAL_PHRASES,
            handle_all_idiom_path.open("w", encoding="utf-8"),
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )
    else:
        pinyin = pinyin or HANDLE_ANSWER_PHRASES[idiom]["pinyin"].copy()
    if hard:
        if idiom in HANDLE_COMMON_PHRASES:
            HANDLE_COMMON_PHRASES.remove(idiom)
            json.dump(
                HANDLE_COMMON_PHRASES,
                handle_common_idiom_path.open("w", encoding="utf-8"),
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
            )
    else:
        if (idiom not in HANDLE_COMMON_PHRASES) and (hard is not None):
            HANDLE_COMMON_PHRASES.append(idiom)
            json.dump(
                HANDLE_COMMON_PHRASES,
                handle_common_idiom_path.open("w", encoding="utf-8"),
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
            )

    HANDLE_ANSWER_PHRASES[idiom] = {
        "explanation": explanation,
        "pinyin": (
            pinyin := (
                pinyin
                or [
                    j
                    for i in py_get_pinyin(idiom, style=Style.TONE3, v_to_u=True)
                    for j in i
                ]
            )
        ),
    }
    json.dump(
        HANDLE_ANSWER_PHRASES,
        handle_answer_path.open("w", encoding="utf-8"),
        ensure_ascii=False,
        indent=4,
        sort_keys=True,
    )
    return not existance, explanation, pinyin


def legal_idiom(word: str) -> bool:
    return word in HANDLE_LEGAL_PHRASES


def random_idiom(is_hard: bool = False) -> Tuple[str, str]:
    answer = random.choice(HANDLE_LEGAL_PHRASES if is_hard else HANDLE_COMMON_PHRASES)
    return answer, HANDLE_ANSWER_PHRASES[answer]["explanation"]


# fmt: off
# 声母
INITIALS = [
    "zh", "z", "y", "x", "w", "t", "sh", "s", "r", "q", "p",
    "n", "m", "l", "k", "j", "h", "g", "f", "d", "ch", "c", "b"
]
# 韵母
FINALS = [
    "ün", "üe", "üan", "ü", "uo", "un", "ui", "ue", "uang",
    "uan", "uai","ua", "ou", "iu", "iong", "ong", "io", "ing",
    "in", "ie", "iao", "iang", "ian", "ia", "er", "eng", "en",
    "ei", "ao", "ang", "an", "ai", "u", "o", "i", "e", "a"
]
# fmt: on


def split_pinyin(py: str) -> Tuple[str, str, str]:
    """
    py: 输入的拼音
    return: 返回一个三元组，分别表示该拼音的声母，韵母，声调
    """

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
    return initial, final, tone


def get_pinyin(
    idiom: str,
) -> List[Tuple[str, str, str]]:
    """
    idiom: 输入的汉字
    return: 返回一个元组，每个元素是一个三元组，分别表示该汉字的声母，韵母，声调
    """

    return [
        split_pinyin(py)
        for py in (
            wordbase_updater(idiom, explanation=None, pinyin=None, hard=None)[2]
            if HANDLE_ANSWER_PHRASES.get(idiom, None)
            else [
                j
                for i in py_get_pinyin(idiom, style=Style.TONE3, v_to_u=True)
                for j in i
            ]
        )
    ]


def save_jpg(frame: IMG) -> BytesIO:
    output = BytesIO()
    frame = frame.convert("RGB")
    frame.save(output, format="jpeg")
    return output


def load_font(name: str, fontsize: int) -> FreeTypeFont:
    return ImageFont.truetype(str(fonts_dir / name), fontsize, encoding="utf-8")
