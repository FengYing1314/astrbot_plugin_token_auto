#  AstrBot Token管理插件

## 目前支持兼容openai及其他返回usage字段的llm
## 📝 功能特性

- 🔄 自动统计每个会话的token使用量
- 📊 显示每条消息的token使用情况
- 🔁 支持会话重置时自动重置token计数
- ⚠️ token使用量达到上限时通知管理员
- 🛠️ 支持管理员手动重置token计数
- 💾 自动保存并加载token统计数据
- 📈 Token使用趋势图生成
- 📤 支持导出Token记录(JSON/CSV)
- 💰 自定义Token计费
- 🛡️ 群组及用户级别Token配额管理
- 🚨 Token异常使用检测

## 💡 使用方法

| 命令 | 说明 | 权限 |
|------|------|------|
| `/token` | 开启/关闭token显示 | 所有人 |
| `/token_check` | 查看当前会话token使用情况 | 所有人 |
| `/reset_tokens` | 重置所有token计数 | 仅管理员 |
| `/token_all` | 查看所有会话的token使用情况 | 仅管理员 |
| `/token_chart` | 生成Token使用趋势图 | 所有人 |
| `/export_tokens [json/csv]` | 导出Token记录 | 仅管理员 |

## ⚙️ 配置说明

- `admin_ids` - 接收通知的管理员QQ号列表
- `max_tokens` - token使用上限配置
  - `group` - 群聊消息token使用上限
  - `private` - 私聊消息token使用上限
- `cost_per_token` - 单个Token费用
- `user_limits` - 指定用户Token上限
- `anomaly_threshold` - 单条消息异常阈值

## 🎯 功能规划

### ✅ 已实现功能
- [x] 多管理员支持
- [x] 不同会话类型(群聊/私聊)的token限额设置
- [x] 基础token统计与显示
- [x] token使用预警通知
- [x] Token趋势图与记录导出
- [x] 用户级别限制与异常检测


## 作者
FengYing

## 鸣谢
感谢 [astrbot_plugin_token_calculator](https://github.com/rinen0721/astrbot_plugin_token_calculator) 项目提供参考

# 支持

[帮助文档](https://astrbot.soulter.top/center/docs/%E5%BC%80%E5%8F%91/%E6%8F%92%E4%BB%B6%E5%BC%80%E5%8F%91/)
