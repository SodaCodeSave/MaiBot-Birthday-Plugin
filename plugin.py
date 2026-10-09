"""生日插件 — 生日当天向回复提示词注入「今天是你的生日」提醒。

配置生日的月份与日期；生日当天，插件通过 `maisaka.replyer.before_request`
Hook 把提示词追加到 replyer 的额外回复要求中，让模型在生成回复时知道今天是自己的生日。
"""

from calendar import monthrange
from datetime import date
from typing import Any, Dict, Tuple

from maibot_sdk import CONFIG_RELOAD_SCOPE_SELF, Command, Field, HookHandler, MaiBotPlugin, PluginConfigBase
from maibot_sdk.types import ErrorPolicy, HookMode, HookOrder

DEFAULT_PROMPT_TEMPLATE = (
    "今天是{month}月{day}日，是你的生日。"
    "收到生日祝福时可以自然地开心回应，也可以适当提到今天是你自己的生日；"
    "没人提起时不必每条消息都强调。"
)


class PluginSectionConfig(PluginConfigBase):
    """插件基础配置。"""

    __ui_label__ = "插件"
    __ui_icon__ = "settings"
    __ui_order__ = 0

    config_version: str = Field(default="1.0.0", description="配置版本")
    enabled: bool = Field(default=True, description="是否启用插件")


class BirthdaySectionConfig(PluginConfigBase):
    """生日配置。"""

    __ui_label__ = "生日"
    __ui_icon__ = "cake"
    __ui_order__ = 1

    month: int = Field(default=1, description="生日月份（1-12）")
    day: int = Field(default=1, description="生日日期（1-31，2月29日仅在闰年生效）")
    prompt_template: str = Field(
        default=DEFAULT_PROMPT_TEMPLATE,
        description="生日当天注入的提示词模板，支持 {month} 和 {day} 占位符",
    )


class BirthdayPluginConfig(PluginConfigBase):
    """生日插件完整配置。"""

    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)
    birthday: BirthdaySectionConfig = Field(default_factory=BirthdaySectionConfig)


class BirthdayPlugin(MaiBotPlugin):
    """生日提示插件。"""

    config_model = BirthdayPluginConfig

    async def on_load(self) -> None:
        """处理插件加载：校验配置并记录当前生日设置。"""

        if not self._is_valid_birthday():
            self._log_invalid_birthday()
        self._warn_impossible_date()
        self.ctx.logger.info(
            "生日插件已加载：生日=%d月%d日，启用=%s",
            self.config.birthday.month,
            self.config.birthday.day,
            self.config.plugin.enabled,
        )

    async def on_unload(self) -> None:
        """处理插件卸载。"""

        self.ctx.logger.info("生日插件已卸载")

    async def on_config_update(self, scope: str, config_data: Dict[str, Any], version: str) -> None:
        """处理配置热重载：配置已由 Runner 更新，这里只做校验与日志。"""

        del config_data
        del version

        if scope != CONFIG_RELOAD_SCOPE_SELF:
            return
        if not self._is_valid_birthday():
            self._log_invalid_birthday()
        self._warn_impossible_date()
        self.ctx.logger.info(
            "生日配置已更新：生日=%d月%d日，启用=%s",
            self.config.birthday.month,
            self.config.birthday.day,
            self.config.plugin.enabled,
        )

    def _is_valid_birthday(self) -> bool:
        """检查生日月份与日期是否在合法范围内。"""

        birthday = self.config.birthday
        return 1 <= birthday.month <= 12 and 1 <= birthday.day <= 31

    def _log_invalid_birthday(self) -> None:
        """记录非法生日配置，由加载与配置更新入口调用以免每条回复都刷屏。"""

        self.ctx.logger.warning(
            "生日配置无效：month=%s day=%s（要求 month 为 1-12、day 为 1-31）",
            self.config.birthday.month,
            self.config.birthday.day,
        )

    def _has_impossible_date(self) -> bool:
        """判断配置的日期在对应月份中是否存在（如 2 月 30 日、4 月 31 日不存在）。

        月份天数按闰年 2000 年计算，因此 2 月 29 日不被判为不存在。
        """

        birthday = self.config.birthday
        if not self._is_valid_birthday():
            return False
        return birthday.day > monthrange(2000, birthday.month)[1]

    def _warn_impossible_date(self) -> None:
        """对永远不会生效的日期给出 warning，由加载与配置更新入口调用。"""

        if not self._has_impossible_date():
            return
        self.ctx.logger.warning(
            "生日配置日期在对应月份中不存在：month=%s day=%s，该配置永远不会生效",
            self.config.birthday.month,
            self.config.birthday.day,
        )

    def _is_birthday(self, today: date) -> bool:
        """判断给定日期是否为配置的生日当天。"""

        birthday = self.config.birthday
        if not self.config.plugin.enabled or not self._is_valid_birthday():
            return False
        return (today.month, today.day) == (birthday.month, birthday.day)

    def _render_prompt(self) -> str:
        """按当前配置渲染注入提示词，替换 {month} 与 {day} 占位符。"""

        birthday = self.config.birthday
        return (
            birthday.prompt_template.strip()
            .replace("{month}", str(birthday.month))
            .replace("{day}", str(birthday.day))
        )

    @HookHandler(
        "maisaka.replyer.before_request",
        name="birthday_prompt_injector",
        description="生日当天向回复提示词追加「今天是你的生日」提醒",
        mode=HookMode.BLOCKING,
        order=HookOrder.LATE,
        error_policy=ErrorPolicy.SKIP,
    )
    async def inject_birthday_prompt(self, **kwargs: Any) -> Dict[str, Any]:
        """在 replyer 请求模型前把生日提示合并进已有的额外回复要求。"""

        if not self._is_birthday(date.today()):
            return {"action": "continue", "modified_kwargs": kwargs}

        hint = self._render_prompt()
        if not hint:
            return {"action": "continue", "modified_kwargs": kwargs}

        existing_prompt = str(kwargs.get("extra_prompt") or "").strip()
        kwargs["extra_prompt"] = f"{existing_prompt}\n\n{hint}".strip() if existing_prompt else hint
        self.ctx.logger.debug("已注入生日提示：%s", hint)
        return {"action": "continue", "modified_kwargs": kwargs}

    @Command("birthday", description="查看生日配置与今日注入状态", pattern=r"^/birthday$")
    async def handle_birthday(self, **kwargs: Any) -> Tuple[bool, str, int]:
        """返回当前生日配置、今日是否注入以及注入内容预览。"""

        stream_id = str(kwargs.get("stream_id") or "")
        today = date.today()
        birthday = self.config.birthday

        if not self.config.plugin.enabled:
            status = "插件已停用，不会注入提示"
        elif not self._is_valid_birthday():
            status = "生日配置无效，不会注入提示"
        elif self._is_birthday(today):
            status = "今天会注入生日提示"
        else:
            status = "今天不会注入生日提示"

        lines = [
            f"配置的生日：{birthday.month}月{birthday.day}日",
            f"启用状态：{'已启用' if self.config.plugin.enabled else '已停用'}",
            f"今天（{today.month}月{today.day}日）：{status}",
            f"注入内容预览：{self._render_prompt() or '（提示词模板为空，不注入）'}",
        ]
        await self.ctx.send.text("\n".join(lines), stream_id)
        return True, "已返回生日配置状态", 2


def create_plugin() -> BirthdayPlugin:
    """创建生日插件实例。

    Returns:
        BirthdayPlugin: 新的生日插件实例。
    """

    return BirthdayPlugin()
