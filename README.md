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

**以下命令需要加[命令前缀](https://nonebot.dev/docs/appendices/config#command-start-和-command-separator) (默认为`/`)，可自行设置为空，此处省略**

```
@机器人 + 猜成语/handle
```


### 规则

你有十次的机会猜一个四字词语；

每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；

汉字的右上角标的数字1、2、3、4分别对应一、二、三、四声；

青色 表示其出现在答案中且在正确的位置；

橙色 表示其出现在答案中但不在正确的位置，至多着色 **此单词中有这个字母的数量** 次；

每个格子的 汉字、声母、韵母、声调 都会独立进行颜色的指示。

当四个格子都为青色时，你便赢得了游戏！

可发送“结束”结束游戏；可发送“提示”查看提示。

使用 `--strict` 选项开启成语检查，即猜测的短语必须是成语，如：

```
handle --strict
```
注：`--strict` 仅在 `handle_strict_mode` 被设置为 `False` 时生效。


### 示例

<div align="left">
  <img src="https://s2.loli.net/2023/01/29/SplDtuFNQaKvEHR.png" width="400" />
</div>


### 说明

#### 橙色块着色规则为：

```
橙色块至多着色 此成语中有这个元素的数量 次。
```
同时其满足：

```
橙色块着色数量 + 青色块着色数量 <= 此成语中有这个元素的数量。
```

类似Wordle，这意味着：

**如果答案是 `zu2 bu4 chu1 hu4`。**

玩家猜测 `hu1 xx1 xx1 xx1`(x代表无关)，则

`h` 标为橙色。

`1` 声在第 3 格标记青色，其他为灰色。（因为着青色的数量达到最大值 1）

玩家猜测 `hu4 hu4 su4 su4`，则

第 1 个 `h` 着橙色，第 2 个 `h` 着灰色。（因为着青色的数量达到最大值 1）

`4` 声在第 2、4 格着青色，在第 1、3 格着灰色。（因为着青色的数量达到最大值 2）

四个 `u` 全部标记为青色。


#### 特殊标记

在旧版 nonebot-plugin-handle(<0.3.2) 中，若出现连续标黄的拼音，玩家无法判断其是出自同一个字还是不同的字，如下图所示。

![image.png](https://s2.loli.net/2023/12/04/NOydSPkYQAh3HDV.png)

> 更新后，若所猜拼音下，出现双下划线，则代表该声母/韵母是出自同一个出现在答案中的字。

这张图片的含义是：成语中出现了 xin 这个拼音的字，但位置不正确。

![image.png](https://s2.loli.net/2023/12/04/wDuFtoGST9byMZp.png)

这张图片的含义是：成语中，所猜位置是 xin1，但不是新这个字。（正确答案是心）

![image.png](https://s2.loli.net/2023/12/04/VcrwlLaS3ht9uj7.png)


### 特别感谢

- [antfu/handle](https://github.com/antfu/handle) A Chinese Hanzi variation of Wordle - 汉字 Wordle
- [AllanChain/chinese-wordle](https://github.com/AllanChain/chinese-wordle) Chinese idiom wordle game | 仿 wordle 的拼成语游戏
