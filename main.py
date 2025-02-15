import json
from typing import Dict, Optional
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.event.filter import command, permission_type, PermissionType
from astrbot.api.provider import LLMResponse
from astrbot.core.message.components import Plain
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent

@register("token_auto", "FengYing", "Token使用监控与管理插件", "1.0.0")
class TokenAutoPlugin(Star):
    """Token使用监控与管理插件
    
    功能:
    - 自动统计每个会话的token使用量
    - 显示每条消息的token使用情况
    - 支持会话重置时自动重置token计数
    - token使用量达到上限时通知管理员
    - 支持管理员手动重置token计数
    """

    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        # 初始化配置和计数器
        self.token_counts: Dict[str, int] = {}  # 会话token计数
        self.total_tokens: int = 0   # 总token计数
        self.session_tokens: Dict[str, int] = {} # 会话token记录
        self.last_usage: Dict[str, int] = {}    # 最后一次使用记录
        
        # 从配置读取设置
        self.admin_ids = config.get("admin_ids", [])
        self.max_tokens = {
            "group": config.get("max_tokens", {}).get("group", 100000),
            "private": config.get("max_tokens", {}).get("private", 50000)
        }
        
        # token显示控制
        self.show_tokens = False
        self._token_msg = ""
        self._is_llm_resp = False
        
        logger.info(
            f"Token监控插件已启动\n"
            f"群聊限制: {self.max_tokens['group']}\n"
            f"私聊限制: {self.max_tokens['private']}\n"
            f"管理员数量: {len(self.admin_ids)}"
        )

    def _get_session_info(self, event: AstrMessageEvent) -> tuple[str, str, int]:
        """获取会话信息
        
        Returns:
            tuple: (会话类型, 会话ID, token限制)
        """
        is_group = bool(event.message_obj.group_id)
        session_type = "group" if is_group else "private"
        session_id = f"{session_type}_{event.message_obj.group_id or event.get_sender_id()}"
        token_limit = self.max_tokens[session_type]
        return session_type, session_id, token_limit

    async def _update_token_counts(self, event: AstrMessageEvent, tokens: int, session_id: str) -> None:
        """更新token计数"""
        self.total_tokens += tokens
        self.session_tokens[session_id] = self.session_tokens.get(session_id, 0) + tokens
        self.last_usage[session_id] = tokens
        self.token_counts[session_id] = self.token_counts.get(session_id, 0) + tokens

    async def _format_token_message(self, usage) -> str:
        """格式化token使用信息"""
        return (
            f"\n💫 Token消耗: {usage.total_tokens} "
            f"(完成: {usage.completion_tokens}, "
            f"提示: {usage.prompt_tokens})"
        )

    @command("token")
    async def toggle_token_display(self, event: AstrMessageEvent):
        """开启/关闭token显示"""
        self.show_tokens = not self.show_tokens
        yield event.plain_result(
            f"⚙️ Token显示状态\n"
            f"━━━━━━━━━━━━━━\n"
            f"当前状态: {'🟢 开启' if self.show_tokens else '🔴 关闭'}\n"
            f"━━━━━━━━━━━━━━"
        )

    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp: LLMResponse):
        """处理LLM响应,更新token统计"""
        try:
            # 验证token信息是否可用
            completion = resp.raw_completion
            if not completion or not hasattr(completion, 'usage') or not completion.usage:
                return
            
            # 获取会话信息
            session_type, session_id, token_limit = self._get_session_info(event)
            current_usage = completion.usage.total_tokens
            
            # 更新计数
            await self._update_token_counts(event, current_usage, session_id)
            
            # 设置显示消息
            if self.show_tokens:
                self._token_msg = await self._format_token_message(completion.usage)
                self._is_llm_resp = True

            # 检查是否超限并通知
            if self.token_counts[session_id] >= token_limit:
                await self._notify_admin(event, session_type, session_id, token_limit)

        except Exception as e:
            logger.error(f"Token统计出错: {str(e)}")

    async def _notify_admin(self, event: AstrMessageEvent, session_type: str, session_id: str, limit: int):
        """通知管理员token超限"""
        if event.get_platform_name() != "aiocqhttp":
            return
            
        try:
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            notify_msg = (
                f"⚠️ Token使用预警\n"
                f"━━━━━━━━━━━━━━\n"
                f"📈 当前使用量: {self.token_counts[session_id]}/{limit}\n"
                f"⛔ 会话类型: {session_type}\n" 
                f"👤 最后发送者: {event.get_sender_name()}\n"
                f"🔑 会话ID: {session_id}\n"
                f"━━━━━━━━━━━━━━\n"
                f"💡 使用 /reset_tokens 重置计数"
            )

            # 尝试通知所有管理员直到成功
            for admin_id in self.admin_ids:
                try:
                    await client.api.call_action('send_private_msg', 
                        user_id=int(admin_id),
                        message=notify_msg
                    )
                    logger.info(f"已发送Token预警给管理员: {admin_id}")
                    return
                except Exception as e:
                    if "请先添加对方为好友" in str(e):
                        continue
                    logger.error(f"发送通知给管理员 {admin_id} 失败: {str(e)}")
            
            logger.error("所有管理员通知失败")
        except Exception as e:
            logger.error(f"通知管理员失败: {str(e)}")

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        """在消息发送前添加token信息"""
        if self.show_tokens and self._is_llm_resp:
            try:
                event.get_result().chain.append(Plain(self._token_msg))
                self._is_llm_resp = False
            except Exception as e:
                logger.error(f"添加Token信息失败: {str(e)}")

    @filter.command("reset")
    async def handle_reset(self, event: AstrMessageEvent):
        """处理会话重置,同时重置token计数"""
        try:
            # 获取会话信息
            session_type, session_id, _ = self._get_session_info(event)
            old_session = self.session_tokens.get(session_id, 0)
            old_count = self.token_counts.get(session_id, 0)
            
            # 重置计数
            if session_id in self.session_tokens:
                self.total_tokens = max(0, self.total_tokens - old_session)
                del self.session_tokens[session_id]
                del self.last_usage[session_id]
                del self.token_counts[session_id]

            # 记录日志
            logger.info(f"重置会话: {session_id} (会话: {old_session}, 计数: {old_count})")
            
            # 返回结果 - 增加会话类型和ID显示
            yield event.plain_result(
                f"📊 Token重置结果\n"
                f"━━━━━━━━━━━━━━\n"
                f"🔑 会话类型: {session_type}\n"
                f"📍 会话ID: {session_id}\n"
                f"🔄 会话tokens: {old_session}\n"
                f"📈 计数tokens: {old_count}\n"
                f"✅ 清除完成\n"
                f"━━━━━━━━━━━━━━"
            )
            
        except Exception as e:
            logger.error(f"重置token失败: {str(e)}")
            yield event.plain_result("❌ 重置失败，请查看日志")

    @command("token_check") 
    async def check_tokens(self, event: AstrMessageEvent):
        """查看token使用情况"""
        _, session_id, token_limit = self._get_session_info(event)
        session_count = self.session_tokens.get(session_id, 0)
        last_count = self.last_usage.get(session_id, 0)
        
        yield event.plain_result(
            f"📊 Token使用统计\n"
            f"━━━━━━━━━━━━━━\n"
            f"💫 会话类型: {'群聊' if event.message_obj.group_id else '私聊'}\n"
            f"📈 当前会话: {session_count} tokens\n"
            f"🔄 上次消耗: {last_count} tokens\n"
            f"📶 总量上限: {self.total_tokens}/{token_limit}\n"
            f"⚙️ 显示状态: {'🟢 开启' if self.show_tokens else '🔴 关闭'}\n"
            f"━━━━━━━━━━━━━━\n"
            f"💡 提示: 使用 /token 可以开关token显示"
        )

    @command("token_all")
    @permission_type(PermissionType.ADMIN)
    async def list_all_tokens(self, event: AstrMessageEvent):
        """查看所有会话的token使用情况"""
        if not self.token_counts:
            yield event.plain_result(
                f"📊 Token使用统计\n"
                f"━━━━━━━━━━━━━━\n"
                f"ℹ️ 当前无任何会话记录\n"
                f"━━━━━━━━━━━━━━"
            )
            return
            
        # 按使用量降序排序
        sorted_sessions = sorted(
            self.token_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 生成统计信息
        details = []
        total_used = 0
        for session_id, count in sorted_sessions:
            session_type = "群聊" if "group" in session_id else "私聊"
            details.append(
                f"{'👥' if 'group' in session_id else '👤'} "
                f"{session_type}: {session_id}\n"
                f"📈 使用量: {count} tokens"
            )
            total_used += count

        # 构建返回消息
        result = (
            f"📊 Token总览统计\n"
            f"━━━━━━━━━━━━━━\n"
            f"💫 活跃会话: {len(sorted_sessions)}\n"
            f"📊 总使用量: {total_used} tokens\n"
            f"━━━━━━━━━━━━━━\n"
        )
        
        # 添加详细信息
        result += "\n━━ 会话详情 ━━\n"
        result += "\n\n".join(details)
        result += "\n━━━━━━━━━━━━━━"
            
        yield event.plain_result(result)
