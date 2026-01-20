"""Notification service for Discord and Telegram."""
from typing import List, Optional
from loguru import logger
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Connection


class NotificationService:
    """Service for sending notifications."""

    def __init__(self, db: AsyncSession):
        """Initialize notification service."""
        self.db = db

    async def _get_connection(self, connection_id: int) -> Optional[Connection]:
        """Get connection by ID."""
        result = await self.db.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def send_discord(self, webhook_url: str, title: str, message: str, color: int = 0x00FF00) -> bool:
        """Send a Discord notification via webhook."""
        try:
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "footer": {"text": "SeedArr"},
            }
            payload = {"embeds": [embed]}

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"Discord notification sent: {title}")
                return True

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    async def send_telegram(self, bot_token: str, chat_id: str, message: str) -> bool:
        """Send a Telegram notification."""
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"Telegram notification sent to {chat_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    async def notify(self, connection_ids: List[int], title: str, message: str) -> dict:
        """Send notifications to multiple connections."""
        results = {"success": [], "failed": []}

        for conn_id in connection_ids:
            connection = await self._get_connection(conn_id)
            if not connection or not connection.enabled:
                results["failed"].append({"id": conn_id, "reason": "Not found or disabled"})
                continue

            success = False
            if connection.type == "discord":
                # URL is the webhook URL
                success = await self.send_discord(connection.url, title, message)
            elif connection.type == "telegram":
                # URL contains bot token, api_key contains chat_id
                bot_token = connection.url.split("/")[-1] if "bot" in connection.url else connection.url
                chat_id = connection.api_key
                if chat_id:
                    full_message = f"<b>{title}</b>\n\n{message}"
                    success = await self.send_telegram(bot_token, chat_id, full_message)
                else:
                    results["failed"].append({"id": conn_id, "reason": "Missing chat_id"})
                    continue

            if success:
                results["success"].append(conn_id)
            else:
                results["failed"].append({"id": conn_id, "reason": "Send failed"})

        return results

    async def test_discord(self, webhook_url: str) -> dict:
        """Test Discord webhook."""
        success = await self.send_discord(
            webhook_url,
            "Test Notification",
            "This is a test notification from SeedArr.",
            color=0x0099FF,
        )
        return {
            "success": success,
            "message": "Test notification sent" if success else "Failed to send test notification",
        }

    async def test_telegram(self, bot_token: str, chat_id: str) -> dict:
        """Test Telegram notification."""
        success = await self.send_telegram(
            bot_token,
            chat_id,
            "<b>Test Notification</b>\n\nThis is a test notification from SeedArr.",
        )
        return {
            "success": success,
            "message": "Test notification sent" if success else "Failed to send test notification",
        }
