# 生日插件

在配置的生日当天，向麦麦生成回复的提示词中注入「今天是你的生日」提醒。

- 注入时机：`maisaka.replyer.before_request`（replyer 请求模型前）
- 注入方式：追加到已有的额外回复要求之后，不覆盖其他插件写入的内容
- 生效范围：仅生日当天、且插件启用、日期合法、模板非空时注入

## 安装

1. 把本仓库根目录整个复制到 MaiBot 的 `plugins/` 目录下（克隆或直接复制均可）：
   ```
   <MaiBot根目录>/
   └── plugins/
       └── <本仓库根目录>/
           ├── _manifest.json
           ├── plugin.py
           └── README.md
   ```
   MaiBot 按 `_manifest.json` 识别插件，目录名任意、不影响加载；为便于对照文档，建议将目录命名为 `birthday_plugin`。
2. 启动 MaiBot（`uv run bot.py`），插件会被自动发现并加载；首次加载会在插件目录下生成运行时配置 `config.toml`。

## 启用

两种方式任选其一：

- WebUI：「插件管理」中找到「生日插件」，开启启用开关。
- 配置文件：编辑 `plugins/birthday_plugin/config.toml`：
  ```toml
  [plugin]
  config_version = "1.0.0"
  enabled = true
  ```

## 配置

同一份 `config.toml` 中的 `[birthday]` 段，或在 WebUI 的插件配置页编辑：

```toml
[birthday]
month = 10      # 生日月份，1-12
day = 8         # 生日日期，1-31（2月29日仅在闰年生效）
prompt_template = "今天是{month}月{day}日，是你的生日。收到生日祝福时可以自然地开心回应，也可以适当提到今天是你自己的生日；没人提起时不必每条消息都强调。"
```

- `prompt_template` 支持 `{month}`、`{day}` 两个占位符，会分别替换为配置的月份和日期。
- 保存后插件会收到配置热重载回调，无需重启。

## 命令

| 命令 | 说明 |
| --- | --- |
| `/birthday` | 查看配置的生日、启用状态、今天是否注入，以及注入内容预览 |

## 常见问题

**Q：今天是配置的生日，为什么回复里没有体现？**
依次检查：`[plugin] enabled` 是否为 `true`；`month`/`day` 是否合法（1-12 / 1-31）；`prompt_template` 是否为空。可在聊天里发 `/birthday` 直接查看判定结果。

**Q：配置了 2 月 29 日，平时为什么不生效？**
2 月 29 日按精确日期匹配，仅在闰年的 2 月 29 日当天注入。

**Q：注入会覆盖其他插件的要求吗？**
不会。生日提示以追加方式合入已有的 `extra_prompt`，原有内容保留在前。

**Q：怎么确认真的注入了？**
把日志级别调到 debug，生日当天每次回复生成前会打印「已注入生日提示：…」；或用 `/birthday` 查看「注入内容预览」。

**Q：改了配置要重启吗？**
不需要。保存 `config.toml` 或在 WebUI 保存后会触发热重载，插件日志会输出「生日配置已更新」。
