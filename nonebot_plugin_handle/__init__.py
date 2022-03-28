import re
import shlex
import asyncio
from io import BytesIO
from dataclasses import dataclass
from asyncio import TimerHandle
from typing import Dict, List, Optional, NoReturn

from nonebot.matcher import Matcher
from nonebot.exception import ParserExit
from nonebot.typing import T_State
from nonebot.rule import Rule, to_me, ArgumentParser
from nonebot import on_command, on_shell_command, on_message
from nonebot.params import ShellCommandArgv, CommandArg, EventPlainText, State
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    GroupMessageEvent,
    Message,
    MessageSegment,
)

from .data_source import Handle, GuessResult
from .utils import random_idiom


__help__plugin_name__ = "handle"
__des__ = "汉字Wordle 猜成语"
__cmd__ = f"""
@我 + “猜成语”开始游戏；
你有十次的机会猜一个四字词语；
每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；
青色 表示其出现在答案中且在正确的位置；
橙色 表示其出现在答案中但不在正确的位置；
当四个格子都为青色时，你便赢得了游戏！
可发送“结束”结束游戏；可发送“提示”查看提示。
""".strip()
__short_cmd__ = "@我 猜成语"
__example__ = """
@小Q 猜成语
""".strip()
__usage__ = f"{__des__}\n\nUsage:\n{__cmd__}\n\nExample:\n{__example__}"


parser = ArgumentParser("handle", description="猜成语")
parser.add_argument("--hint", action="store_true", help="提示")
parser.add_argument("--stop", action="store_true", help="结束游戏")
parser.add_argument("idiom", nargs="?", help="成语")


@dataclass
class Options:
    hint: bool = False
    stop: bool = False
    idiom: str = ""


games: Dict[str, Handle] = {}
timers: Dict[str, TimerHandle] = {}

handle = on_shell_command("handle", parser=parser, block=True, priority=13)


@handle.handle()
async def _(
    matcher: Matcher, event: MessageEvent, argv: List[str] = ShellCommandArgv()
):
    await handle_handle(matcher, event, argv)


def get_cid(event: MessageEvent):
    return (
        f"group_{event.group_id}"
        if isinstance(event, GroupMessageEvent)
        else f"private_{event.user_id}"
    )


def game_running(event: MessageEvent) -> bool:
    cid = get_cid(event)
    return bool(games.get(cid, None))


def match_idiom(msg: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fa5]{4}", msg))


def get_idiom_input(state: T_State = State(), msg: str = EventPlainText()) -> bool:
    if match_idiom(msg):
        state["idiom"] = msg
        return True
    return False


def shortcut(cmd: str, argv: List[str] = [], **kwargs):
    command = on_command(cmd, **kwargs, block=True, priority=12)

    @command.handle()
    async def _(matcher: Matcher, event: MessageEvent, msg: Message = CommandArg()):
        try:
            args = shlex.split(msg.extract_plain_text().strip())
        except:
            args = []
        await handle_handle(matcher, event, argv + args)


shortcut("猜成语", rule=to_me())
shortcut("提示", ["--hint"], aliases={"给个提示"}, rule=game_running)
shortcut("结束", ["--stop"], aliases={"停", "停止游戏", "结束游戏"}, rule=game_running)


idiom_matcher = on_message(
    Rule(game_running) & get_idiom_input, block=True, priority=12
)


@idiom_matcher.handle()
async def _(matcher: Matcher, event: MessageEvent, state: T_State = State()):
    idiom: str = state["idiom"]
    await handle_handle(matcher, event, [idiom])


async def stop_game(matcher: Matcher, cid: str):
    timers.pop(cid, None)
    if games.get(cid, None):
        game = games.pop(cid)
        msg = "猜成语超时，游戏结束"
        if len(game.guessed) >= 1:
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


async def handle_handle(matcher: Matcher, event: MessageEvent, argv: List[str]):
    async def send(
        message: Optional[str] = None, image: Optional[BytesIO] = None
    ) -> NoReturn:
        if not (message or image):
            await matcher.finish()
        msg = Message()
        if image:
            msg.append(MessageSegment.image(image))
        if message:
            msg.append(message)
        await matcher.finish(msg)

    try:
        args = parser.parse_args(argv)
    except ParserExit as e:
        if e.status == 0:
            await send(__usage__)
        await send()

    options = Options(**vars(args))

    cid = get_cid(event)
    if not games.get(cid, None):
        game = Handle(random_idiom())
        games[cid] = game
        set_timeout(matcher, cid)
        await send(f"你有{game.times}次机会猜一个四字成语，请发送成语", game.draw())

    if options.stop:
        game = games.pop(cid)
        msg = "游戏已结束"
        if len(game.guessed) >= 1:
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
    else:
        await send(image=game.draw())
