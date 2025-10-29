import requests
import os
from dotenv import load_dotenv
import re
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Class để gửi thông báo qua Telegram Bot.
    
    Attributes:
        bot_token (str): Bot Token từ BotFather trên Telegram
        chat_id (str): Chat ID của người nhận
        parse_mode (str): Chế độ parse message (MarkdownV2, Markdown, HTML)
        silent (bool): Nếu True, không in thông báo ra console
    """
    
    def __init__(self, bot_token: str = None, chat_id: str = None, 
                 parse_mode: str = "MarkdownV2", silent: bool = False):
        """Khởi tạo TelegramNotifier.
        
        Args:
            bot_token (str): Bot Token từ BotFather. Nếu None, lấy từ .env
            chat_id (str): Chat ID của người nhận. Nếu None, lấy từ .env
            parse_mode (str): Chế độ parse message. Default: "MarkdownV2"
            silent (bool): Không in log ra console. Default: False
        """
        self.bot_token = bot_token or os.getenv("BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("CHAT_ID")
        self.parse_mode = parse_mode
        self.silent = silent
        
        if not self.bot_token or not self.chat_id:
            error_msg = "BOT_TOKEN hoặc CHAT_ID không được định nghĩa"
            if not self.silent:
                logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape các ký tự đặc biệt cho MarkdownV2.
        
        Args:
            text (str): Text cần escape
            
        Returns:
            str: Text đã được escape
        """
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)
    
    def send(self, message: str, parse_mode: str = None, 
             disable_notification: bool = False) -> bool:
        """Gửi thông báo qua Telegram.
        
        Args:
            message (str): Nội dung thông báo cần gửi
            parse_mode (str): Chế độ parse cho message này (override default)
            disable_notification (bool): Gửi thông báo im lặng (không có sound)
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        # Sử dụng parse_mode từ tham số hoặc default của instance
        current_parse_mode = parse_mode or self.parse_mode
        
        # Escape nếu dùng MarkdownV2
        if current_parse_mode == "MarkdownV2":
            message = self.escape_markdown(message)
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": current_parse_mode,
            "disable_notification": disable_notification
        }
        
        try:
            response = requests.post(self.api_url, data=payload)
            response.raise_for_status()
            if not self.silent:
                logger.info(f"Telegram sent: {message}")
            return True
        except requests.exceptions.RequestException as e:
            if not self.silent:
                logger.error(f"Telegram error: {e}")
            return False
    
    def send_html(self, message: str, disable_notification: bool = False) -> bool:
        """Gửi thông báo với HTML formatting.
        
        Args:
            message (str): Nội dung HTML
            disable_notification (bool): Gửi im lặng
            
        Returns:
            bool: True nếu thành công
        """
        return self.send(message, parse_mode="HTML", 
                        disable_notification=disable_notification)
    
    def send_plain(self, message: str, disable_notification: bool = False) -> bool:
        """Gửi thông báo plain text (không format).
        
        Args:
            message (str): Nội dung plain text
            disable_notification (bool): Gửi im lặng
            
        Returns:
            bool: True nếu thành công
        """
        return self.send(message, parse_mode=None, 
                        disable_notification=disable_notification)
    
    def send_signal(self, symbol: str, signal_type: str, price: float, 
                   additional_info: dict = None) -> bool:
        """Gửi thông báo tín hiệu trading với format chuẩn.
        
        Args:
            symbol (str): Tên symbol (vd: EURUSD)
            signal_type (str): Loại tín hiệu (BUY, SELL, etc)
            price (float): Giá hiện tại
            additional_info (dict): Thông tin bổ sung
            
        Returns:
            bool: True nếu thành công
        """
        emoji = "🟢" if signal_type.upper() == "BUY" else "🔴"
        
        message = f"{emoji} SIGNAL DETECTED\n\n"
        message += f"Symbol: {symbol}\n"
        message += f"Type: {signal_type.upper()}\n"
        message += f"Price: {price}\n"
        
        if additional_info:
            message += "\nAdditional Info:\n"
            for key, value in additional_info.items():
                message += f"- {key}: {value}\n"
        
        return self.send_plain(message)
    
    def set_silent(self, silent: bool):
        """Thay đổi chế độ silent.
        
        Args:
            silent (bool): True để tắt console log
        """
        self.silent = silent
    
    def set_parse_mode(self, parse_mode: str):
        """Thay đổi parse mode mặc định.
        
        Args:
            parse_mode (str): "MarkdownV2", "Markdown", "HTML", hoặc None
        """
        self.parse_mode = parse_mode


# Convenience function để sử dụng như function cũ
def PushNotification(message: str, silent: bool = False, 
                    bot_token: str = None, chat_id: str = None, 
                    parse_mode: str = "MarkdownV2") -> bool:
    """Function wrapper để tương thích với code cũ.
    
    Args:
        message (str): Nội dung thông báo
        silent (bool): Không in log
        bot_token (str): Bot token (từ .env nếu None)
        chat_id (str): Chat ID (từ .env nếu None)
        parse_mode (str): Parse mode
        
    Returns:
        bool: True nếu thành công
    """
    try:
        notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id,
                                    parse_mode=parse_mode, silent=silent)
        return notifier.send(message)
    except ValueError:
        if not silent:
            print("❌ Lỗi: BOT_TOKEN hoặc CHAT_ID không được định nghĩa")
        return False