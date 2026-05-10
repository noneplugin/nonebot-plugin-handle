import asyncio
from asyncio import TimerHandle
from typing import Any, Dict, Annotated

from nonebot import on_regex, require
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import EventToMe, Depends, RegexDict
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.rule import to_me
from nonebot.utils import run_sync
from nonebot.permission import SUPERUSER

from typing_extensions import Annotated

require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")

from nonebot_plugin_alconna import (
    AlcMatches,
    Alconna,
    At,
    Image,
    Option,
    Text,
    UniMessage,
    on_alconna,
    store_true,
    Args,
    Arparma,
)
from nonebot_plugin_uninfo import Uninfo

from .config import Config, handle_config
from .data_source import GuessResult, Handle
from .utils import (
    v_to_u,
    random_idiom,
    wordbase_updater,
    HANDLE_COMMON_PHRASES,
    HANDLE_LEGAL_PHRASES,
)

__plugin_meta__ = PluginMetadata(
    name="猜成语",
    description="汉字 Wordle 猜成语",
    usage=(
        "@我 + “猜成语”开始游戏；\n"
        "你有十次的机会猜一个四字词语；\n"
        "每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；\n"
        "青色 表示其出现在答案中且在正确的位置；\n"
        "橙色 表示其出现在答案中但不在正确的位置；\n"
        "每个格子的 汉字、声母、韵母、声调 都会独立进行颜色的指示。\n"
        "当四个格子都为青色时，你便赢得了游戏！\n"
        "可发送“结束”结束游戏；可发送“提示”查看提示。\n"
        "使用 --strict|-s 选项开启非默认的成语检查，即猜测的短语必须是成语，\n"
        "如：猜成语 --strict\n"
        "使用 --difficult|-d 选项开启困难词库\n"
        "管理员可以使用 新成语、成语答案 两个命令进行成语词库添加和答案查看"
    ),
    type="application",
    homepage="https://github.com/noneplugin/nonebot-plugin-handle",
    config=Config,
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna", "nonebot_plugin_uninfo"
    ),
)


games: Dict[str, Handle] = {}
timers: Dict[str, TimerHandle] = {}


def get_user_id(uninfo: Uninfo) -> str:
    return f"{uninfo.scope}_{uninfo.self_id}_{uninfo.scene_path}"


UserId = Annotated[str, Depends(get_user_id)]


# 游戏运行判断规则
def game_is_running(user_id: UserId) -> bool:
    return user_id in games


def game_not_running(user_id: UserId) -> bool:
    return user_id not in games


# 游戏过程中的功能实现
def stop_game(user_id: str):
    if timer := timers.pop(user_id, None):
        timer.cancel()
    games.pop(user_id, None)


async def stop_game_timeout(matcher: Matcher, user_id: str):
    game = games.get(user_id, None)
    stop_game(user_id)
    if game:
        msg = "猜成语超时，游戏结束。"
        if len(game.guessed_idiom) >= 1:
            msg += f"\n{game.result}"
        await matcher.finish(msg)


def set_timeout(matcher: Matcher, user_id: str, timeout: float = 300):
    if timer := timers.get(user_id, None):
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(
        timeout, lambda: asyncio.ensure_future(stop_game_timeout(matcher, user_id))
    )
    timers[user_id] = timer


# ————

handle_alc = Alconna(
    "handle",
    Option("-s|--strict", default=False, action=store_true),
    Option("-d|--difficult", default=False, action=store_true),
)

handle_matcher = on_alconna(
    handle_alc,
    aliases=("猜成语",),
    rule=(
        (to_me() & game_not_running)
        if handle_config.handle_require_tome
        else (game_not_running)
    ),
    use_cmd_start=True,
    block=True,
    priority=13,
)


@handle_matcher.handle()
async def _(
    result: Arparma,
    matcher: Matcher,
    user_id: UserId,
    alc_matches: AlcMatches,
    to_me: bool = EventToMe(),
):

    header_match = str(alc_matches.header_match.result)
    command = str(handle_alc.command)
    if not (to_me or bool(header_match.rstrip(command))):
        # 既不是对机器人说话，也不是以命令开头……
        logger.debug("非 To me 命令，忽略")
        matcher.block = False
        await matcher.finish()

    # nonebot.logger.info(result.options)
    is_strict = handle_config.handle_strict_mode or result.options["strict"].value
    idiom, explanation = random_idiom(result.options["difficult"].value)
    game = Handle(idiom, explanation, strict=is_strict)

    games[user_id] = game
    set_timeout(matcher, user_id)

    msg = Text(
        "你有{}次机会猜一个四字成语，".format(game.times)
        + ("发送有效成语以参与游戏。" if is_strict else "发送任意四字词语以参与游戏。")
    ) + Image(raw=await run_sync(game.draw)())
    await msg.send()


# ————

handle_hint_matcher = on_alconna(
    "handle_hint",
    aliases=("提示", "猜成语提示"),
    rule=game_is_running,
    use_cmd_start=True,
    block=True,
    priority=13,
)


@handle_hint_matcher.handle()
async def _(matcher: Matcher, user_id: UserId):
    game = games[user_id]
    set_timeout(matcher, user_id)

    await UniMessage.image(raw=await run_sync(game.draw_hint)()).send()


# ————

handle_stop_matcher = on_alconna(
    "handle_stop",
    aliases=("结束", "结束游戏", "结束猜成语"),
    rule=game_is_running,
    use_cmd_start=True,
    block=True,
    priority=13,
)


@handle_stop_matcher.handle()
async def _(matcher: Matcher, user_id: UserId):
    game = games[user_id]
    stop_game(user_id)

    msg = "游戏已结束"
    if len(game.guessed_idiom) >= 1:
        msg += f"\n{game.result}"
    await matcher.finish(msg)


# ————

handle_idiom_matcher = on_regex(
    r"^(?P<idiom>[\u4e00-\u9fa5]{4})$",
    rule=game_is_running,
    block=True,
    priority=14,
)


@handle_idiom_matcher.handle()
async def _(
    matcher: Matcher,
    uninfo: Uninfo,
    user_id: UserId,
    matched: Dict[str, Any] = RegexDict(),
):
    game = games[user_id]
    set_timeout(matcher, user_id)

    idiom = str(matched["idiom"])
    result = game.guess(idiom)

    if result in [GuessResult.WIN, GuessResult.LOSS]:
        stop_game(user_id)
        await UniMessage.template(
            (
                "恭喜{user}猜出了成语！"
                if result == GuessResult.WIN
                else "很遗憾，没有人猜出来呢"
            )
            + "\n{result}\n{image}"
        ).format(
            user="你" if uninfo.scene.is_private else At("user", uninfo.user.id),
            result=game.result,
            image=Image(raw=await run_sync(game.draw)()),
        ).send()

    elif result == GuessResult.DUPLICATE:
        await matcher.finish("你已经猜过这个成语了呢")

    elif result == GuessResult.ILLEGAL:
        await matcher.finish("你确定“{}”是个成语吗？".format(idiom))

    else:
        await UniMessage.image(raw=await run_sync(game.draw)()).send()


# ————

handle_update_pinyin_matcher = on_alconna(
    Alconna(
        "handle_update_pinyin",
        Args["idiom", str, ""],
        Args["pinyin1", str, ""],
        Args["pinyin2", str, ""],
        Args["pinyin3", str, ""],
        Args["pinyin4", str, ""],
    ),
    aliases=(
        "更正拼音",
        "更正成语拼音",
        "更新猜成语词库拼音",
        "猜成语更新拼音",
        "更新猜成语拼音",
        "更新成语拼音",
        "更正猜成语拼音",
    ),
    use_cmd_start=True,
    permission=SUPERUSER,
    block=True,
    priority=13,
)


@handle_update_pinyin_matcher.handle()
async def _(
    result: Arparma,
):

    if not (
        (idiom := result.main_args["idiom"])
        and (pinyin1 := result.main_args["pinyin1"])
        and (pinyin2 := result.main_args["pinyin2"])
        and (pinyin3 := result.main_args["pinyin3"])
        and (pinyin4 := result.main_args["pinyin4"])
    ):
        await handle_update_pinyin_matcher.finish(
            "用法：更正拼音 <成语> <拼音1> <拼音2> <拼音3> <拼音4>"
        )

    if idiom not in HANDLE_LEGAL_PHRASES:
        await handle_update_pinyin_matcher.finish(
            "未在词库中找到该成语，请使用 `新成语 <成语>` 来添加成语"
        )

    _, explanation, pinyin_now = wordbase_updater(
        idiom,
        explanation=None,
        pinyin=v_to_u([pinyin1, pinyin2, pinyin3, pinyin4]),
        hard=None,
    )

    await handle_update_pinyin_matcher.finish(
        "成功修改：{}\n当前词库总数：{}个，普通模式成语：{}个\n当前成语信息如下：{}".format(
            idiom,
            len(HANDLE_LEGAL_PHRASES),
            len(HANDLE_COMMON_PHRASES),
            "\n\t释义：{}\n\t拼音：{}".format(explanation, " ".join(pinyin_now)),
        )
    )


# ————

handle_update_idiom_matcher = on_alconna(
    Alconna(
        "handle_update_idiom",
        Option(
            "-e|--explanation",
            default="",
            args=Args["explanation", str, ""],
        ),
        Option(
            "-d|--difficult",
            default=False,
            action=store_true,
        ),
        Args["idiom", str, ""],
    ),
    aliases=("新成语", "新增成语", "猜成语新增成语"),
    use_cmd_start=True,
    permission=SUPERUSER,
    block=True,
    priority=13,
)


@handle_update_idiom_matcher.handle()
async def _(
    result: Arparma,
):

    if not (idiom := result.main_args["idiom"]):
        await handle_update_idiom_matcher.finish(
            "用法：新成语 <成语> [-e|--explanation <释义>] [-d|--difficult]"
        )

    existance, explanation, pinyin_now = wordbase_updater(
        idiom,
        explanation=(result.options["explanation"].args["explanation"] or None),
        pinyin=None,
        hard=(hard := result.options["difficult"].value),
    )

    await handle_update_idiom_matcher.finish(
        "成功{}：[{}词汇]{}\n当前词库总数：{}个，普通模式成语：{}个\n当前成语信息如下：{}".format(
            "修改" if existance else "新增",
            "困难" if hard else "普通",
            idiom,
            len(HANDLE_LEGAL_PHRASES),
            len(HANDLE_COMMON_PHRASES),
            "\n\t释义：{}\n\t拼音：{}".format(explanation, " ".join(pinyin_now)),
        )
    )


# ————

handle_answer_matcher = on_alconna(
    Alconna(
        "handle_answer",
        Option(
            "-g|--group",
            default="Now",
            args=Args["group", str, "Now"],
        ),
        Option(
            "-l|--list",
            default=False,
            action=store_true,
        ),
    ),
    aliases=("成语答案", "猜成语答案"),
    # rule=game_is_running,
    use_cmd_start=True,
    permission=SUPERUSER,
    block=True,
    priority=13,
)


@handle_answer_matcher.handle()
async def _(
    result: Arparma,
    user_id: UserId,
):

    if handle_config.handle_superuser_get_answer:

        if result.options["list"].value:
            await handle_answer_matcher.finish(
                UniMessage.text(
                    "\n".join(
                        "`{}`，答案“{}”".format(i, j.idiom) for i, j in games.items()
                    )
                )
            )
            return

        try:
            if result.options["group"].args["group"] == "Now":
                session_numstr = user_id
            else:
                await handle_answer_matcher.finish(
                    UniMessage.text("暂不支持指定群组")  # TODO: 指定群组获取答案
                )

        except:
            session_numstr = user_id

        if session_numstr in games.keys():
            await handle_answer_matcher.finish(
                UniMessage.text(games[session_numstr].idiom)
            )
        else:
            await handle_answer_matcher.finish(
                UniMessage.text("{} 不存在开局的游戏".format(session_numstr))
            )

    else:
        await handle_answer_matcher.finish(UniMessage.text("本机器人不许可超管作弊"))
