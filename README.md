# nonebot-plugin-handle

适用于 [Nonebot2](https://github.com/nonebot/nonebot2) 的 汉字Wordle 猜成语插件


### 安装

- 使用 nb-cli

```
nb plugin install nonebot_plugin_handle
```

- 使用 pip

```
pip install nonebot_plugin_handle
```


### 使用

**以下命令需要加[命令前缀](https://v2.nonebot.dev/docs/api/config#Config-command_start) (默认为`/`)，可自行设置为空**

```
@机器人 + 猜成语
```

你有十次的机会猜一个四字词语；

每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；

青色 表示其出现在答案中且在正确的位置；

橙色 表示其出现在答案中但不在正确的位置；

每个格子的 汉字、声母、韵母、声调 都会独立进行颜色的指示。

当四个格子都为青色时，你便赢得了游戏！

可发送“结束”结束游戏；可发送“提示”查看提示。

使用 --strict 选项开启成语检查，即猜测的短语必须是成语，如：

```
@机器人 猜成语 --strict
```


或使用 `handle` 指令：

```
handle [--hint] [--stop] [--strict] [idiom]
```


### 示例

<div align="left">
  <img src="https://s2.loli.net/2023/01/29/SplDtuFNQaKvEHR.png" width="400" />
</div>


### 特别感谢

- [antfu/handle](https://github.com/antfu/handle) A Chinese Hanzi variation of Wordle - 汉字 Wordle
- [AllanChain/chinese-wordle](https://github.com/AllanChain/chinese-wordle) Chinese idiom wordle game | 仿 wordle 的拼成语游戏
