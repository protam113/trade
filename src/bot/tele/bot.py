import requests
import os
from dotenv import load_dotenv
import re

load_dotenv()

def escape_markdown(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def bot_tele(message: str, silent: bool = False, bot_token: str = None, chat_id: str = None, parse_mode: str = "MarkdownV2" ) -> bool:
    """Gửi thông báo qua Telegram Bot.

    Parameters:
        message (str): Nội dung thông báo cần gửi.
        silent (bool): Nếu True, không in thông báo ra console. Default: False.
        bot_token (str): Bot Token từ BotFather trên Telegram. Default: None (lấy từ .env).
        chat_id (str): Chat ID của người nhận. Default: None (lấy từ .env).

    Returns:
        bool: True nếu gửi thành công, False nếu thất bại.
    """
    # Lấy token và chat_id từ biến môi trường nếu không được truyền trực tiếp
    bot_token = bot_token or os.getenv("BOT_TOKEN")
    chat_id = chat_id or os.getenv("CHAT_ID")

    if not bot_token or not chat_id:
        if not silent:
            print("❌ Lỗi: BOT_TOKEN hoặc CHAT_ID không được định nghĩa")
        return False

    # Escape nếu dùng MarkdownV2
    if parse_mode == "MarkdownV2":
        message = escape_markdown(message)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        if not silent:
            print(f"✅ Telegram: {message}")
        return True
    except requests.exceptions.RequestException as e:
        if not silent:
            print(f"❌ Lỗi Telegram: {e}")
        return False
