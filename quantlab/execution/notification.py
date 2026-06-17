"""
Notification Center — 通知中心

支持：
  - Telegram
  - Discord
  - Email
  - 本地日志（默认）

通知事件：
  - 开仓
  - 平仓
  - 风险触发
  - 策略停止
  - 订单成交
  - 自定义

用法：
    from quantlab.execution.notification import NotificationCenter, NotificationLevel

    notifier = NotificationCenter()
    notifier.add_channel(LogChannel())

    # 添加 Telegram
    notifier.add_channel(TelegramChannel(token="xxx", chat_id="xxx"))

    notifier.notify(
        level=NotificationLevel.INFO,
        title="开仓",
        message="BUY 0.5 BTC @ 50000",
        metadata={"symbol": "BTCUSDT", "qty": 0.5},
    )
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.notification")


# ------------------------------------------------------------------
# NotificationLevel
# ------------------------------------------------------------------

class NotificationLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Notification:
    """通知消息"""
    level: NotificationLevel
    title: str
    message: str
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    category: str = ""  # order / fill / risk / strategy / system

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "category": self.category,
        }

    def format_text(self) -> str:
        """格式化为纯文本"""
        lines = [
            f"[{self.level.value}] {self.title}",
            self.message,
        ]
        if self.metadata:
            for k, v in self.metadata.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Channel 抽象
# ------------------------------------------------------------------

class NotificationChannel:
    """通知渠道基类"""

    name: str = "BASE"
    min_level: NotificationLevel = NotificationLevel.INFO

    def __init__(self, min_level: Optional[NotificationLevel] = None) -> None:
        if min_level is not None:
            self.min_level = min_level

    def send(self, notification: Notification) -> bool:
        """发送通知，返回是否成功"""
        raise NotImplementedError

    def _should_send(self, notification: Notification) -> bool:
        """检查级别是否达到发送门槛"""
        levels = [
            NotificationLevel.DEBUG,
            NotificationLevel.INFO,
            NotificationLevel.WARNING,
            NotificationLevel.ERROR,
            NotificationLevel.CRITICAL,
        ]
        return levels.index(notification.level) >= levels.index(self.min_level)


# ------------------------------------------------------------------
# LogChannel
# ------------------------------------------------------------------

class LogChannel(NotificationChannel):
    """日志渠道（默认）"""

    name = "LOG"

    def send(self, notification: Notification) -> bool:
        if not self._should_send(notification):
            return True

        msg = notification.format_text()
        if notification.level == NotificationLevel.DEBUG:
            logger.debug(msg)
        elif notification.level == NotificationLevel.INFO:
            logger.info(msg)
        elif notification.level == NotificationLevel.WARNING:
            logger.warning(msg)
        elif notification.level == NotificationLevel.ERROR:
            logger.error(msg)
        elif notification.level == NotificationLevel.CRITICAL:
            logger.critical(msg)
        return True


# ------------------------------------------------------------------
# TelegramChannel
# ------------------------------------------------------------------

class TelegramChannel(NotificationChannel):
    """
    Telegram 渠道

    依赖：
      pip install requests

    配置：
      1) 找 @BotFather 创建 bot，拿 token
      2) 把 bot 加入群组或私聊，拿 chat_id
    """

    name = "TELEGRAM"

    def __init__(
        self,
        token: str,
        chat_id: str,
        min_level: Optional[NotificationLevel] = None,
    ) -> None:
        super().__init__(min_level=min_level)
        self.token = token
        self.chat_id = chat_id

    def send(self, notification: Notification) -> bool:
        if not self._should_send(notification):
            return True

        try:
            import requests
        except ImportError:
            logger.error("requests not installed for TelegramChannel")
            return False

        text = notification.format_text()
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"```\n{text}\n```",
            "parse_mode": "Markdown",
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                logger.error(
                    f"Telegram send failed: {resp.status_code} {resp.text}"
                )
                return False
            return True
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False


# ------------------------------------------------------------------
# DiscordChannel
# ------------------------------------------------------------------

class DiscordChannel(NotificationChannel):
    """
    Discord 渠道（通过 Webhook）

    配置：
      1) Discord 频道设置 → 集成 → Webhook → 新建
      2) 拿到 webhook_url
    """

    name = "DISCORD"

    def __init__(
        self,
        webhook_url: str,
        min_level: Optional[NotificationLevel] = None,
    ) -> None:
        super().__init__(min_level=min_level)
        self.webhook_url = webhook_url

    def send(self, notification: Notification) -> bool:
        if not self._should_send(notification):
            return True

        try:
            import requests
        except ImportError:
            logger.error("requests not installed for DiscordChannel")
            return False

        text = notification.format_text()
        payload = {"content": f"```\n{text}\n```"}

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code not in (200, 204):
                logger.error(
                    f"Discord send failed: {resp.status_code} {resp.text}"
                )
                return False
            return True
        except Exception as e:
            logger.error(f"Discord send error: {e}")
            return False


# ------------------------------------------------------------------
# EmailChannel
# ------------------------------------------------------------------

class EmailChannel(NotificationChannel):
    """
    邮件渠道

    配置：
      smtp_host, smtp_port, username, password
      from_addr, to_addrs
    """

    name = "EMAIL"

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        use_tls: bool = True,
        min_level: Optional[NotificationLevel] = None,
    ) -> None:
        super().__init__(min_level=min_level)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls

    def send(self, notification: Notification) -> bool:
        if not self._should_send(notification):
            return True

        try:
            msg = MIMEText(notification.format_text())
            msg["Subject"] = f"[{notification.level.value}] {notification.title}"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(
                    self.from_addr,
                    self.to_addrs,
                    msg.as_string(),
                )
            return True
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False


# ------------------------------------------------------------------
# NotificationCenter
# ------------------------------------------------------------------

class NotificationCenter:
    """
    通知中心

    管理多个渠道，统一发送。
    """

    def __init__(self) -> None:
        self._channels: List[NotificationChannel] = []
        self._history: List[Notification] = []
        self._max_history = 1000

    def add_channel(self, channel: NotificationChannel) -> None:
        """添加渠道"""
        self._channels.append(channel)
        logger.info(f"NotificationCenter: added channel {channel.name}")

    def remove_channel(self, name: str) -> bool:
        """移除渠道"""
        for i, ch in enumerate(self._channels):
            if ch.name == name:
                self._channels.pop(i)
                return True
        return False

    def notify(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        category: str = "",
    ) -> Notification:
        """
        发送通知

        参数：
          level     级别
          title     标题
          message   内容
          metadata  额外数据
          category  分类（order/fill/risk/strategy/system）
        """
        from datetime import datetime

        notification = Notification(
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
            category=category,
        )

        # 记录历史
        self._history.append(notification)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # 发送到所有渠道
        for channel in self._channels:
            try:
                channel.send(notification)
            except Exception as e:
                logger.error(
                    f"NotificationCenter: channel {channel.name} error: {e}"
                )

        return notification

    # 便捷方法
    def info(self, title: str, message: str, **kwargs) -> Notification:
        return self.notify(NotificationLevel.INFO, title, message, **kwargs)

    def warning(self, title: str, message: str, **kwargs) -> Notification:
        return self.notify(NotificationLevel.WARNING, title, message, **kwargs)

    def error(self, title: str, message: str, **kwargs) -> Notification:
        return self.notify(NotificationLevel.ERROR, title, message, **kwargs)

    def critical(self, title: str, message: str, **kwargs) -> Notification:
        return self.notify(NotificationLevel.CRITICAL, title, message, **kwargs)

    # 查询
    def list_history(
        self,
        category: Optional[str] = None,
        level: Optional[NotificationLevel] = None,
        limit: int = 100,
    ) -> List[Notification]:
        """查询历史通知"""
        result = self._history
        if category:
            result = [n for n in result if n.category == category]
        if level:
            result = [n for n in result if n.level == level]
        return result[-limit:]

    def stats(self) -> Dict[str, Any]:
        return {
            "n_channels": len(self._channels),
            "channels": [ch.name for ch in self._channels],
            "n_history": len(self._history),
        }


# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_global_notifier: Optional[NotificationCenter] = None


def get_notifier() -> NotificationCenter:
    """获取全局 NotificationCenter"""
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = NotificationCenter()
        _global_notifier.add_channel(LogChannel())
    return _global_notifier


def set_notifier(notifier: NotificationCenter) -> None:
    global _global_notifier
    _global_notifier = notifier
