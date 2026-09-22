#!/usr/bin/env python3
"""
Notification module for Reddit Idea Radar
Alerts when Tier 1 ideas are discovered.

Usage:
    from notifier import notify_tier1
    notify_tier1([idea1, idea2, ...])

All methods fail silently — never crashes the main scanner.
"""

import ctypes
import json
import logging
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Windows-only stdlib module; absent on Linux/macOS.
try:
    import winsound
except ImportError:
    winsound = None

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env", override=True)
except ImportError:
    pass

# ============================================================================
# CONFIG
# ============================================================================

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
ALERTS_LOG = Path.home() / "idea-radar-output" / "alerts.log"
DESKTOP_NOTIFICATIONS = True

logger = logging.getLogger("idea-radar-notifier")


# ============================================================================
# DESKTOP NOTIFICATION (Windows toast / MessageBox fallback)
# ============================================================================

def _try_toast(title: str, message: str) -> bool:
    """Try win10toast first, fall back to ctypes MessageBox."""
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            duration=8,
            threaded=True,
        )
        return True
    except Exception:
        pass

    # Fallback: Windows MessageBox (non-blocking with MB_ICONINFORMATION)
    try:
        MB_OK = 0x00000000
        MB_ICONINFORMATION = 0x00000040
        MB_SYSTEMMODAL = 0x00001000
        ctypes.windll.user32.MessageBoxW(
            0,
            message,
            title,
            MB_OK | MB_ICONINFORMATION | MB_SYSTEMMODAL,
        )
        return True
    except Exception:
        return False


def notify_desktop(ideas: list[dict]) -> None:
    """Show desktop notification for Tier 1 ideas."""
    if not DESKTOP_NOTIFICATIONS:
        return

    for idea in ideas:
        title = idea.get("problem", {}).get("title", "New Tier 1 Idea")
        composite = idea.get("scoring", {}).get("composite", "?")
        _try_toast(
            f"TIER 1 — {composite}/10",
            title,
        )


# ============================================================================
# WEBHOOK
# ============================================================================

def notify_webhook(ideas: list[dict]) -> None:
    """POST idea summaries to configured webhook URL."""
    if not WEBHOOK_URL:
        return

    for idea in ideas:
        payload = {
            "event": "tier1_idea",
            "timestamp": datetime.now().isoformat(),
            "idea": {
                "title": idea.get("problem", {}).get("title", ""),
                "description": idea.get("problem", {}).get("description", ""),
                "composite_score": idea.get("scoring", {}).get("composite", 0),
                "market_signal": idea.get("scoring", {}).get("market_signal", 0),
                "subreddit": idea.get("market", {}).get("subreddit", ""),
                "thread_url": idea.get("market", {}).get("thread_url", ""),
                "angle": idea.get("angle", {}).get("type", ""),
                "monetization": idea.get("monetization", {}).get("model", ""),
                "price_point": idea.get("monetization", {}).get("price_point", ""),
            },
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                WEBHOOK_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    logger.warning("Webhook returned %d", resp.status)
        except Exception as e:
            logger.warning("Webhook failed: %s", e)


# ============================================================================
# SOUND ALERT
# ============================================================================

def notify_sound() -> None:
    """Play Windows system sound for Tier 1 discovery."""
    try:
        if sys.platform == "win32" and winsound is not None:
            # Play the Windows "tada" or default exclamation sound
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
        else:
            # Non-Windows: bell character
            print("\a", end="", flush=True)
    except Exception:
        pass


# ============================================================================
# LOG FILE
# ============================================================================

def notify_log(ideas: list[dict]) -> None:
    """Append Tier 1 alerts to log file with timestamp."""
    try:
        ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERTS_LOG, "a", encoding="utf-8") as f:
            for idea in ideas:
                title = idea.get("problem", {}).get("title", "?")
                composite = idea.get("scoring", {}).get("composite", "?")
                subreddit = idea.get("market", {}).get("subreddit", "?")
                thread_url = idea.get("market", {}).get("thread_url", "")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(
                    f"[{timestamp}] TIER 1 | {composite}/10 | {title} | "
                    f"{subreddit} | {thread_url}\n"
                )
    except Exception as e:
        logger.warning("Log write failed: %s", e)


# ============================================================================
# PUBLIC API
# ============================================================================

def notify_tier1(ideas: list[dict]) -> None:
    """
    Main entry point. Notify about Tier 1 ideas via all configured channels.
    All methods fail silently — this function never raises.

    Args:
        ideas: List of Tier 1 idea dicts (same schema as radar output).
    """
    if not ideas:
        return

    # Log first (most important, least likely to fail)
    try:
        notify_log(ideas)
    except Exception:
        pass

    # Sound alert
    try:
        notify_sound()
    except Exception:
        pass

    # Desktop notification
    try:
        notify_desktop(ideas)
    except Exception:
        pass

    # Webhook (optional)
    try:
        notify_webhook(ideas)
    except Exception:
        pass


if __name__ == "__main__":
    # Quick test
    test_ideas = [
        {
            "problem": {"title": "Invoice automation for freelancers", "description": "Test"},
            "scoring": {"composite": 8.7, "market_signal": 9},
            "market": {"subreddit": "r/freelance", "thread_url": "https://reddit.com/test"},
            "angle": {"type": "UX"},
            "monetization": {"model": "SaaS", "price_point": "$19/mo"},
        }
    ]
    print("Testing notifications...")
    notify_tier1(test_ideas)
    print(f"Check log: {ALERTS_LOG}")
