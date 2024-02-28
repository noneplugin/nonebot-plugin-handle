import asyncio
import re
import shlex
from asyncio import TimerHandle
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, NoReturn, Optional

from nonebot import on_command, on_message, on_shell_command, require
from nonebot.adapters import Bot, Event, Message
from nonebot.exception import ParserExit
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import (
    CommandArg,
    CommandStart,
    EventPlainText,
    EventToMe,
    ShellCommandArgv,
)
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.rule import ArgumentParser, Rule
from nonebot.typing import T_State
from nonebot.utils import run_sync

require("nonebot_plugin_saa")
require("nonebot_plugin_session")

from nonebot_plugin_saa import Image, MessageFactory
from nonebot_plugin_session import SessionIdType, extract_session

from .config import Config, handle_config
from .data_source import GuessResult, Handle
from .utils import random_idiom

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
        "使用 --strict 选项开启非默认的成语检查，即猜测的短语必须是成语，如：@我 猜成语 --strict"
    ),
    type="application",
    homepage="https://github.com/noneplugin/nonebot-plugin-handle",
    config=Config,
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_saa", "nonebot_plugin_session"
    ),
    extra={
        "unique_name": "handle",
        "example": "@小Q 猜成语",
        "author": "meetwq <meetwq@gmail.com>",
        "version": "0.3.6",
    },
)


parser = ArgumentParser("handle", description="猜成语")
parser.add_argument("--hint", action="store_true", help="提示")
parser.add_argument("--stop", action="store_true", help="结束游戏")
parser.add_argument("idiom", nargs="?", type=str, default="", help="成语")
parser.add_argument("--strict", action="store_true", help="验证模式，即判断所发送短语是否为成语")


@dataclass
class Options:
    hint: bool = False
    stop: bool = False
    idiom: str = ""
    strict: bool = False


games: Dict[str, Handle] = {}
timers: Dict[str, TimerHandle] = {}

handle = on_shell_command("handle", parser=parser, block=True, priority=13)


@handle.handle()
async def _(
    bot: Bot,
    matcher: Matcher,
    event: Event,
    argv: List[str] = ShellCommandArgv(),
):
    await handle_handle(bot, matcher, event, argv)


def get_cid(bot: Bot, event: Event):
    return extract_session(bot, event).get_id(SessionIdType.GROUP)


def game_running(bot: Bot, event: Event) -> bool:
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
    async def _(bot: Bot, matcher: Matcher, event: Event, msg: Message = CommandArg()):
        try:
            args = shlex.split(msg.extract_plain_text().strip())
        except Exception as e:
            logger.warning(f"shlex.split error: {e}")
            args = []
        await handle_handle(bot, matcher, event, argv + args)


shortcut("猜成语", rule=smart_to_me)
shortcut("提示", ["--hint"], aliases={"给个提示"}, rule=game_running)
shortcut("结束", ["--stop"], aliases={"结束游戏", "停止游戏"}, rule=game_running)


idiom_matcher = on_message(
    Rule(game_running) & get_idiom_input, block=True, priority=14
)


@idiom_matcher.handle()
async def _(
    bot: Bot,
    matcher: Matcher,
    event: Event,
    state: T_State,
):
    idiom: str = state["idiom"]
    await handle_handle(bot, matcher, event, [idiom])


async def stop_game(matcher: Matcher, cid: str):
    timers.pop(cid, None)
    if games.get(cid, None):
        game = games.pop(cid)
        msg = "猜成语超时，游戏结束。"
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
    bot: Bot,
    matcher: Matcher,
    event: Event,
    argv: List[str],
):
    async def send(
        message: Optional[str] = None, image: Optional[BytesIO] = None
    ) -> NoReturn:
        if not (message or image):
            await matcher.finish()

        msg_builder = MessageFactory([])
        if image:
            msg_builder.append(Image(image))
        if message:
            if image:
                message = "\n" + message
            msg_builder.append(message)
        await msg_builder.send()
        await matcher.finish()

    try:
        args = parser.parse_args(argv)
    except ParserExit as e:
        if e.status == 0:
            await send(__plugin_meta__.usage)
        return

    options = Options(**vars(args))

    cid = get_cid(bot, event)
    if not games.get(cid, None):
        is_strict = handle_config.handle_strict_mode or options.strict
        game = Handle(*random_idiom(), strict=is_strict)
        games[cid] = game
        set_timeout(matcher, cid)
        msg = f"你有{game.times}次机会猜一个四字成语，"
        msg += "发送有效成语以参与游戏。" if is_strict else "发送任意四字词语以参与游戏。"
        await send(msg, await run_sync(game.draw)())

    if options.stop:
        game = games.pop(cid)
        msg = "游戏已结束"
        if len(game.guessed_idiom) >= 1:
            msg += f"\n{game.result}"
        await send(msg)

    game = games[cid]
    set_timeout(matcher, cid)

    if options.hint:
        await send(image=await run_sync(game.draw_hint)())

    idiom = options.idiom
    if not match_idiom(idiom):
        await send()

    result = game.guess(idiom)
    if result in [GuessResult.WIN, GuessResult.LOSS]:
        games.pop(cid)
        await send(
            ("恭喜你猜出了成语！" if result == GuessResult.WIN else "很遗憾，没有人猜出来呢")
            + f"\n{game.result}",
            await run_sync(game.draw)(),
        )
    elif result == GuessResult.DUPLICATE:
        await send("你已经猜过这个成语了呢")
    elif result == GuessResult.ILLEGAL:
        await send(f"你确定“{idiom}”是个成语吗？")
    else:
        await send(image=await run_sync(game.draw)())
