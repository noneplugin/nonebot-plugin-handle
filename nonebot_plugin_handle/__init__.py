import re
import shlex
import asyncio
from io import BytesIO
from asyncio import TimerHandle
from dataclasses import dataclass
from typing import Dict, List, Optional, NoReturn, Union

from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.exception import ParserExit
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule, ArgumentParser
from nonebot import on_command, on_shell_command, on_message
from nonebot.params import (
    ShellCommandArgv,
    CommandArg,
    CommandStart,
    EventPlainText,
    EventToMe,
)

from nonebot.adapters.onebot.v11 import Bot as V11Bot
from nonebot.adapters.onebot.v11 import Message as V11Msg
from nonebot.adapters.onebot.v11 import MessageSegment as V11MsgSeg
from nonebot.adapters.onebot.v11 import MessageEvent as V11MEvent
from nonebot.adapters.onebot.v11 import GroupMessageEvent as V11GMEvent

from nonebot.adapters.onebot.v12 import Bot as V12Bot
from nonebot.adapters.onebot.v12 import Message as V12Msg
from nonebot.adapters.onebot.v12 import MessageSegment as V12MsgSeg
from nonebot.adapters.onebot.v12 import MessageEvent as V12MEvent
from nonebot.adapters.onebot.v12 import GroupMessageEvent as V12GMEvent
from nonebot.adapters.onebot.v12 import ChannelMessageEvent as V12CMEvent

from .utils import random_idiom
from .data_source import Handle, GuessResult

__plugin_meta__ = PluginMetadata(
    name="猜成语",
    description="汉字Wordle 猜成语",
    usage=(
        "@我 + “猜成语”开始游戏；\n"
        "你有十次的机会猜一个四字词语；\n"
        "每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；\n"
        "青色 表示其出现在答案中且在正确的位置；\n"
        "橙色 表示其出现在答案中但不在正确的位置；\n"
        "每个格子的 汉字、声母、韵母、声调 都会独立进行颜色的指示。\n"
        "当四个格子都为青色时，你便赢得了游戏！\n"
        "可发送“结束”结束游戏；可发送“提示”查看提示。\n"
        "使用 --strict 选项开启成语检查，即猜测的短语必须是成语，如：@我 猜成语 --strict"
    ),
    extra={
        "unique_name": "handle",
        "example": "@小Q 猜成语",
        "author": "meetwq <meetwq@gmail.com>",
        "version": "0.2.0",
    },
)


parser = ArgumentParser("handle", description="猜成语")
parser.add_argument("--hint", action="store_true", help="提示")
parser.add_argument("--stop", action="store_true", help="结束游戏")
parser.add_argument("--strict", action="store_true", help="严格模式，即判断是否是成语")
parser.add_argument("idiom", nargs="?", type=str, default="", help="成语")


@dataclass
class Options:
    hint: bool = False
    stop: bool = False
    strict: bool = False
    idiom: str = ""


games: Dict[str, Handle] = {}
timers: Dict[str, TimerHandle] = {}

handle = on_shell_command("handle", parser=parser, block=True, priority=13)


@handle.handle()
async def _(
    bot: Union[V11Bot, V12Bot],
    matcher: Matcher,
    event: Union[V11MEvent, V12MEvent],
    argv: List[str] = ShellCommandArgv(),
):
    await handle_handle(bot, matcher, event, argv)


def get_cid(bot: Union[V11Bot, V12Bot], event: Union[V11MEvent, V12MEvent]):
    if isinstance(event, V11MEvent):
        cid = f"{bot.self_id}_{event.sub_type}_"
    else:
        cid = f"{bot.self_id}_{event.detail_type}_"

    if isinstance(event, V11GMEvent) or isinstance(event, V12GMEvent):
        cid += str(event.group_id)
    elif isinstance(event, V12CMEvent):
        cid += f"{event.guild_id}_{event.channel_id}"
    else:
        cid += str(event.user_id)

    return cid


def game_running(
    bot: Union[V11Bot, V12Bot], event: Union[V11MEvent, V12MEvent]
) -> bool:
    cid = get_cid(bot, event)
    return bool(games.get(cid, None))


def match_idiom(msg: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fa5]{4}", msg))


def get_idiom_input(state: T_State, msg: str = EventPlainText()) -> bool:
    if match_idiom(msg):
        state["idiom"] = msg
        return True
    return False


# 命令前缀为空则需要to_me，否则不需要
def smart_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me


def shortcut(cmd: str, argv: List[str] = [], **kwargs):
    command = on_command(cmd, **kwargs, block=True, priority=12)

    @command.handle()
    async def _(
        bot: Union[V11Bot, V12Bot],
        matcher: Matcher,
        event: Union[V11MEvent, V12MEvent],
        msg: Union[V11Msg, V12Msg] = CommandArg(),
    ):
        try:
            args = shlex.split(msg.extract_plain_text().strip())
        except:
            args = []
        await handle_handle(bot, matcher, event, argv + args)


shortcut("猜成语", rule=smart_to_me)
shortcut("提示", ["--hint"], aliases={"给个提示"}, rule=game_running)
shortcut("结束", ["--stop"], aliases={"停止游戏", "结束游戏"}, rule=game_running)


idiom_matcher = on_message(
    Rule(game_running) & get_idiom_input, block=True, priority=14
)


@idiom_matcher.handle()
async def _(
    bot: Union[V11Bot, V12Bot],
    matcher: Matcher,
    event: Union[V11MEvent, V12MEvent],
    state: T_State,
):
    idiom: str = state["idiom"]
    await handle_handle(bot, matcher, event, [idiom])


async def stop_game(matcher: Matcher, cid: str):
    timers.pop(cid, None)
    if games.get(cid, None):
        game = games.pop(cid)
        msg = "猜成语超时，游戏结束"
        if len(game.guessed_idiom) >= 1:
            msg += f"\n{game.result}"
        await matcher.finish(msg)


def set_timeout(matcher: Matcher, cid: str, timeout: float = 300):
    timer = timers.get(cid, None)
    if timer:
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(
        timeout, lambda: asyncio.ensure_future(stop_game(matcher, cid))
    )
    timers[cid] = timer


async def handle_handle(
    bot: Union[V11Bot, V12Bot],
    matcher: Matcher,
    event: Union[V11MEvent, V12MEvent],
    argv: List[str],
):
    async def send(
        message: Optional[str] = None, image: Optional[BytesIO] = None
    ) -> NoReturn:
        if not (message or image):
            await matcher.finish()

        if isinstance(bot, V11Bot):
            msg = V11Msg()
            if image:
                msg.append(V11MsgSeg.image(image))
        else:
            msg = V12Msg()
            if image:
                resp = await bot.upload_file(
                    type="data", name="wordle", data=image.getvalue()
                )
                file_id = resp["file_id"]
                msg.append(V12MsgSeg.image(file_id))

        if message:
            msg.append(message)
        await matcher.finish(msg)

    try:
        args = parser.parse_args(argv)
    except ParserExit as e:
        if e.status == 0:
            await send(__plugin_meta__.usage)
        await send()

    options = Options(**vars(args))

    cid = get_cid(bot, event)
    if not games.get(cid, None):
        game = Handle(*random_idiom(), strict=options.strict)
        games[cid] = game
        set_timeout(matcher, cid)
        await send(f"你有{game.times}次机会猜一个四字成语，请发送成语", game.draw())

    if options.stop:
        game = games.pop(cid)
        msg = "游戏已结束"
        if len(game.guessed_idiom) >= 1:
            msg += f"\n{game.result}"
        await send(msg)

    game = games[cid]
    set_timeout(matcher, cid)

    if options.hint:
        await send(image=game.draw_hint())

    idiom = options.idiom
    if not match_idiom(idiom):
        await send()

    result = game.guess(idiom)
    if result in [GuessResult.WIN, GuessResult.LOSS]:
        games.pop(cid)
        await send(
            ("恭喜你猜出了成语！" if result == GuessResult.WIN else "很遗憾，没有人猜出来呢")
            + f"\n{game.result}",
            game.draw(),
        )
    elif result == GuessResult.DUPLICATE:
        await send("你已经猜过这个成语了呢")
    elif result == GuessResult.ILLEGAL:
        await send(f"你确定“{idiom}”是个成语吗？")
    else:
        await send(image=game.draw())
