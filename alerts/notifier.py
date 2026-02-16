"""
Alert Notification Dispatch
============================
Sends alerts via desktop notifications, Discord, and Telegram.
"""

import json
from typing import List
from logger import get_logger
from alerts.detector import Alert

log = get_logger("alerts.notifier")


def send_desktop_notification(title: str, body: str):
    """Send a Windows desktop toast notification via plyer."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=body[:256],  # Windows toast has length limits
            timeout=10,
            app_name="Options Dashboard",
        )
        log.debug("Desktop notification sent: %s", title)
    except ImportError:
        log.warning("plyer not installed — skipping desktop notification")
    except Exception as e:
        log.warning("Desktop notification failed: %s", e)


def send_discord_webhook(webhook_url: str, message: str):
    """Send a message to a Discord channel via webhook."""
    if not webhook_url:
        return

    try:
        import httpx
        payload = {"content": message}
        resp = httpx.post(webhook_url, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            log.debug("Discord webhook sent successfully")
        else:
            log.warning("Discord webhook returned %d: %s", resp.status_code, resp.text[:200])
    except ImportError:
        log.warning("httpx not installed — skipping Discord webhook")
    except Exception as e:
        log.warning("Discord webhook failed: %s", e)


def send_telegram(bot_token: str, chat_id: str, message: str):
    """Send a message via Telegram Bot API."""
    if not bot_token or not chat_id:
        return

    try:
        import httpx
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        resp = httpx.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            log.debug("Telegram message sent successfully")
        else:
            log.warning("Telegram API returned %d: %s", resp.status_code, resp.text[:200])
    except ImportError:
        log.warning("httpx not installed — skipping Telegram")
    except Exception as e:
        log.warning("Telegram send failed: %s", e)


def dispatch_alerts(alerts: List[Alert]):
    """Route alerts to all configured notification channels.

    Reads configuration to determine which channels are enabled.
    Also saves alerts to the database for the dashboard to display.
    """
    if not alerts:
        return

    # Load config
    try:
        from config import load_config
        cfg = load_config()
        desktop_enabled = cfg.alerts.desktop_notifications
        discord_url = cfg.alerts.discord_webhook
        telegram_token = cfg.alerts.telegram_bot_token
        telegram_chat = cfg.alerts.telegram_chat_id
    except Exception:
        desktop_enabled = True
        discord_url = ""
        telegram_token = ""
        telegram_chat = ""

    # Save alerts to database
    try:
        from db.storage import save_alert
        for alert in alerts:
            save_alert(alert.ticker, alert.alert_type, alert.message, alert.details)
    except Exception as e:
        log.warning("Could not save alerts to database: %s", e)

    # Group alerts for bulk notifications
    critical_alerts = [a for a in alerts if a.severity == 'critical']
    warning_alerts = [a for a in alerts if a.severity == 'warning']
    info_alerts = [a for a in alerts if a.severity == 'info']

    # Desktop notifications — only for critical and warning
    if desktop_enabled:
        important_alerts = critical_alerts + warning_alerts
        if important_alerts:
            # Batch into a single notification
            title = f"🔔 {len(important_alerts)} Trading Alert{'s' if len(important_alerts) > 1 else ''}"
            body = "\n".join(a.message for a in important_alerts[:5])  # Max 5 in notification
            if len(important_alerts) > 5:
                body += f"\n... and {len(important_alerts) - 5} more"
            send_desktop_notification(title, body)

    # Discord — all alerts
    if discord_url:
        message_parts = []
        if critical_alerts:
            message_parts.append("🚨 **CRITICAL**\n" + "\n".join(a.message for a in critical_alerts))
        if warning_alerts:
            message_parts.append("⚠️ **WARNING**\n" + "\n".join(a.message for a in warning_alerts))
        if info_alerts:
            message_parts.append("ℹ️ **INFO**\n" + "\n".join(a.message for a in info_alerts[:10]))

        if message_parts:
            send_discord_webhook(discord_url, "\n\n".join(message_parts))

    # Telegram — critical and warning only
    if telegram_token and telegram_chat:
        important = critical_alerts + warning_alerts
        if important:
            msg = "<b>🔔 Options Dashboard Alerts</b>\n\n"
            msg += "\n".join(a.message for a in important[:10])
            send_telegram(telegram_token, telegram_chat, msg)

    log.info(
        "Dispatched %d alerts (%d critical, %d warning, %d info)",
        len(alerts), len(critical_alerts), len(warning_alerts), len(info_alerts)
    )
