# astrbot_plugin_token_auto

AstrBot Token使用监控与管理插件，提供以下功能：
- 自动统计每个会话的token使用量
- 显示每条消息的token使用情况
- 支持会话重置时自动重置token计数
- token使用量达到上限时通知管理员
- 支持管理员手动重置token计数
- 使用了ai开发（真爽）

## 使用方法

- `/token` - 开启/关闭token显示
- `/token_check` - 查看当前token使用情况 
- `/reset_tokens` - 重置所有token计数(仅管理员)

## 配置项

- `admin_id` - 接收通知的管理员QQ号
- `max_tokens` - token使用上限，达到此值将通知管理员

## 作者
FengYing

## 鸣谢
感谢 [astrbot_plugin_token_calculator](https://github.com/rinen0721/astrbot_plugin_token_calculator) 项目提供参考

## 画饼计划 🎯

### 即将推出
- [ ] 自定义 token 使用量提醒阈值
- [ ] 多管理员支持
- [ ] 不同会话类型(群聊/私聊)的 token 限额设置

### 未来规划
- [ ] Token 使用趋势图表生成
- [ ] 导出 Token 使用记录(CSV/JSON格式)
- [ ] 自定义 Token 计费规则
- [ ] 群组 Token 配额管理
- [ ] 用户级别的 Token 使用限制
- [ ] Web 面板数据可视化
- [ ] Token 使用异常检测和告警

# 支持

[帮助文档](https://astrbot.soulter.top/center/docs/%E5%BC%80%E5%8F%91/%E6%8F%92%E4%BB%B6%E5%BC%80%E5%8F%91/)
