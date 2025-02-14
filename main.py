import asyncio
import json
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.event.filter import command, permission_type, PermissionType
from astrbot.api.provider import LLMResponse, ProviderRequest
from astrbot.core.message.components import Plain

@register("auto_reset", "FengYing", "更加详细的Token使用监控与重置插件", "1.0.0")
class AutoResetPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.total_tokens = 0
        self.session_tokens = {}
        self.last_usage = {}
        self.admin_id = config.get("admin_id", "")
        self.max_tokens = config.get("max_tokens", 100000)
        self.show_tokens = False
        self.current_token_msg = ""
        self.is_llm_response = False
        logger.info(f"Token监控插件已启动 - 最大限制: {self.max_tokens}")

    @command("token")
    async def toggle_token_display(self, event: AstrMessageEvent):
        """开启/关闭token显示"""
        self.show_tokens = not self.show_tokens
        yield event.plain_result(f"Token信息显示已{'开启' if self.show_tokens else '关闭'}")

    @filter.command("reset")
    async def handle_reset(self, event: AstrMessageEvent):
        """处理重置命令"""
        try:
            session_id = event.unified_msg_origin
            if session_id in self.session_tokens:
                old_count = self.session_tokens[session_id]
                self.total_tokens = max(0, self.total_tokens - old_count)
                del self.session_tokens[session_id]
                if session_id in self.last_usage:
                    del self.last_usage[session_id]
                logger.info(f"重置对话: {session_id} token已清除 ({old_count} -> 0)")
        except Exception as e:
            logger.error(f"重置token计数时出错: {str(e)}")

    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp: LLMResponse):
        """处理LLM响应,更新token统计"""
        try:
            completion = resp.raw_completion
            if completion is None or not hasattr(completion, 'usage'):
                self.current_token_msg = "(无法获取Token用量信息，可能是当前provider不支持)"
                return

            usage = completion.usage
            if not usage:
                self.current_token_msg = "(无法获取Token用量信息，可能是当前provider不支持)"
                return

            # 更新计数
            session_id = event.unified_msg_origin
            current_usage = usage.total_tokens
            self.total_tokens += current_usage
            self.session_tokens[session_id] = self.session_tokens.get(session_id, 0) + current_usage
            self.last_usage[session_id] = current_usage

            # 设置消息提示
            if self.show_tokens:
                self.current_token_msg = (
                    f"\n(completion_tokens:{usage.completion_tokens}, "
                    f"prompt_tokens:{usage.prompt_tokens}, "
                    f"token总消耗:{usage.total_tokens})"
                )
                self.is_llm_response = True

            # 检查是否超过上限
            if self.total_tokens >= self.max_tokens:
                await self._notify_admin(event)

        except Exception as e:
            logger.error(f"Token统计出错: {str(e)}")
            self.current_token_msg = "(TokenCalculator插件无法获取信息或者出现未知错误)"

    async def _notify_admin(self, event: AstrMessageEvent):
        """通知管理员token超限"""
        try:
            if event.get_platform_name() == "aiocqhttp":
                session_id = event.unified_msg_origin
                session_parts = session_id.split(":")
                notify_msg = (
                    f"Token使用量已达到{self.total_tokens}/{self.max_tokens}。\n"
                    f"触发会话: {session_parts[1]} {session_parts[2]}\n"
                    f"最后发送者: {event.get_sender_name()}\n"
                    f"请使用 /reset_tokens 重置计数器。"
                )
                payloads = {
                    "user_id": int(self.admin_id),
                    "message": notify_msg
                }
                await event.bot.api.call_action('send_private_msg', **payloads)
                logger.info(f"已发送管理员通知")
        except Exception as e:
            logger.error(f"发送管理员通知失败: {str(e)}")

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        """在消息发送前添加token信息"""
        if self.show_tokens and self.is_llm_response:
            try:
                event.get_result().chain.append(Plain(self.current_token_msg))
                self.is_llm_response = False
            except Exception as e:
                logger.error(f"添加Token信息出错: {str(e)}")

    @command("reset_tokens")
    @permission_type(PermissionType.ADMIN)
    async def reset_tokens(self, event: AstrMessageEvent):
        """重置所有token计数器"""
        old_count = self.total_tokens
        # 重置所有计数器
        self.total_tokens = 0
        self.session_tokens.clear()
        self.last_usage.clear()
        yield event.plain_result(f"Token计数已重置。原计数: {old_count}")
        
        # 如果在群聊中重置,通知管理员
        if event.get_platform_name() == "aiocqhttp" and "group" in event.unified_msg_origin:
            notify_msg = (
                f"Token计数已重置。\n原计数: {old_count}\n"
                f"重置操作来自: {event.unified_msg_origin}\n"
                f"操作者: {event.get_sender_name()}"
            )
            await event.bot.api.call_action('send_private_msg', **{
                "user_id": int(self.admin_id),
                "message": notify_msg
            })

    @command("token_check") 
    async def check_tokens(self, event: AstrMessageEvent):
        """查看当前token使用量"""
        session_id = event.unified_msg_origin
        session_count = self.session_tokens.get(session_id, 0)
        last_count = self.last_usage.get(session_id, 0)
        yield event.plain_result(
            f"Token使用统计:\n"
            f"- 总量: {self.total_tokens}/{self.max_tokens}\n"
            f"- 当前会话: {session_count}\n"
            f"- 上次使用: {last_count}\n"
            f"Token显示状态: {'开启' if self.show_tokens else '关闭'}\n"
            f"提示: 使用 /token 可以开关token显示"
        )
