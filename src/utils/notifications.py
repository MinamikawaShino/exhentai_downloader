import sys
import threading

from ..i18n import t


def send_notification(title: str, message: str):
    def _notify():
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="ExHentai Downloader",
                timeout=5,
            )
        except Exception:
            pass

    if sys.platform == "win32":
        threading.Thread(target=_notify, daemon=True).start()
