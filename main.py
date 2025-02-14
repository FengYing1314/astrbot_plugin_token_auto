import asyncio
import json
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.event.filter import command, permission_type
from astrbot.api.permission import PermissionType

@register("auto_reset", "YourName", "Token使用监控与重置插件", "1.0.0")
class AutoResetPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.total_tokens = 0
        self.admin_id = config.get("admin_id", "")
        self.max_tokens = config.get("max_tokens", 100000)
        # 监听LLM响应
        self.context.event_bus.subscribe("on_llm_response", self.on_llm_response)
        
    async def on_llm_response(self, event: AstrMessageEvent, response):
        """监听LLM响应,统计token使用量"""
        if response and response.raw_completion:
            # 获取本次对话使用的token
            usage = response.raw_completion.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            self.total_tokens += prompt_tokens + completion_tokens
            
            # 检查是否超过上限
            if self.total_tokens >= self.max_tokens:
                # 构建私聊消息origin
                admin_origin = f"private_{self.admin_id}"
                
                # 发送通知给管理员
                await self.context.send_message(
                    admin_origin,
                    f"Token使用量已达到{self.total_tokens}/{self.max_tokens}。\n"
                    f"请使用 /reset_tokens 重置计数器。"
                )
    
    @command("reset_tokens")
    @permission_type(PermissionType.ADMIN)
    async def reset_tokens(self, event: AstrMessageEvent):
        """重置token计数器"""
        old_count = self.total_tokens
        self.total_tokens = 0
        yield event.plain_result(f"Token计数已重置。原计数: {old_count}")
        
    @command("check_tokens") 
    async def check_tokens(self, event: AstrMessageEvent):
        """查看当前token使用量"""
        yield event.plain_result(
            f"当前Token使用量: {self.total_tokens}/{self.max_tokens}"
        )
