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


### 配置项

> 以下配置项可在 `.env.*` 文件中设置，具体参考 [NoneBot 配置方式](https://nonebot.dev/docs/appendices/config)

#### `handle_strict_mode`
 - 类型：`bool`
 - 默认：`False`
 - 说明：是否启用严格模式，开启后猜测的短语必须是成语

#### `handle_color_enhance`
 - 类型：`bool`
 - 默认：`False`
 - 说明：是否启用色彩增强模式


### 使用

**以下命令需要加[命令前缀](https://nonebot.dev/docs/appendices/config#command-start-和-command-separator) (默认为`/`)，可自行设置为空**

```
@机器人 + 猜成语
```

你有十次的机会猜一个四字词语；

每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；

青色 表示其出现在答案中且在正确的位置；

橙色 表示其出现在答案中但不在正确的位置，至多着色 **此单词中有这个字母的数量** 次；

每个格子的 汉字、声母、韵母、声调 都会独立进行颜色的指示。

当四个格子都为青色时，你便赢得了游戏！

可发送“结束”结束游戏；可发送“提示”查看提示。


或使用 `handle` 指令：

```
handle [--hint] [--stop] [idiom]
```


### 示例

<div align="left">
  <img src="https://s2.loli.net/2023/01/29/SplDtuFNQaKvEHR.png" width="400" />
</div>


### 说明
橙色块着色规则为：

```
橙色块至多着色 此单词中有这个字母的数量 次。
```

类似Wordle，这意味着：

如果答案是 `zu2 bu4 chu1 hu4`。

玩家猜测 `hu1 xx1 xx1 xx1`(x代表无关)，则 h 标为橙色，1 声在第 3 格标记青色，其他为灰色。

玩家猜测 `hu4 hu4 xx4 xx4`，则第 1 个 h 着橙色，第 2 个 h 着灰色。4 声在第 4 格着青色，在第 1 格着橙色，2、3 格着灰色。


### 特别感谢

- [antfu/handle](https://github.com/antfu/handle) A Chinese Hanzi variation of Wordle - 汉字 Wordle
- [AllanChain/chinese-wordle](https://github.com/AllanChain/chinese-wordle) Chinese idiom wordle game | 仿 wordle 的拼成语游戏
