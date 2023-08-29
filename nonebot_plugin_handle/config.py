from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    handle_strict_mode: bool = False
    handle_color_enhance: bool = False


handle_config = Config.parse_obj(get_driver().config.dict())
