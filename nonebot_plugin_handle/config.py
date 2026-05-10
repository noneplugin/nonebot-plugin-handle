from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    handle_strict_mode: bool = False
    """开启严格模式，强制校验成语是否在词库中"""
    handle_color_enhance: bool = False
    """生成的图片采用更鲜艳的颜色"""
    handle_superuser_get_answer: bool = False
    """超级用户可以查看当局答案"""
    handle_require_tome: bool = False
    """玩家必须@机器人"""


handle_config = get_plugin_config(Config)
