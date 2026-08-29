import requests
from loguru import logger
import config

_NTFY_URL = "https://ntfy.sh/{topic}"

_PRIORITY = {"success": "high", "error": "urgent", "warning": "default", "info": "low"}
_TAGS = {"success": "white_check_mark", "error": "rotating_light", "warning": "warning", "info": "information_source"}


def send(title: str, body: str, level: str = "info") -> bool:
    """Send to ntfy.sh (personal) and Telegram channel (public)."""
    _send_ntfy(title, body, level)
    _send_channel(title, body, level)
    return True


def _send_ntfy(title: str, body: str, level: str) -> bool:
    if not config.NTFY_TOPIC:
        return False
    try:
        r = requests.post(
            _NTFY_URL.format(topic=config.NTFY_TOPIC),
            data=body.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": _PRIORITY.get(level, "default"),
                "Tags": _TAGS.get(level, "information_source"),
            },
            timeout=15,
        )
        if not r.ok:
            logger.warning(f"ntfy error {r.status_code}: {r.text}")
        return r.ok
    except Exception as e:
        logger.warning(f"ntfy send failed: {e}")
        return False


def _send_channel(title: str, body: str, level: str) -> bool:
    try:
        from telegram_marketing_bot import post_to_channel
        return post_to_channel(title, body, level)
    except Exception as e:
        logger.warning(f"Telegram channel post failed: {e}")
        return False
