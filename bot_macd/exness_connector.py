"""
Module kết nối Exness qua MetaTrader 5
"""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class ExnessConnector:
    """
    Kết nối với Exness qua MetaTrader 5
    """
    
    def __init__(self, account: int, password: str, server: str):
        """
        Khởi tạo kết nối Exness
        
        Parameters:
        -----------
        account : int
            Số tài khoản MT5
        password : str
            Mật khẩu MT5
        server : str
            Tên server MT5 (VD: "Exness-Demo", "Exness-Real")
        """
        self.account = account
        self.password = password
        self.server = server
        self.connected = False
        
    def connect(self) -> bool:
        """
        Kết nối với MetaTrader 5
        
        Returns:
        --------
        bool
            True nếu kết nối thành công
        """
        logger.info(f"Đang kết nối với MT5...")
        logger.info(f"  Account: {self.account}")
        logger.info(f"  Server: {self.server}")
        
        if not mt5.initialize():
            error = mt5.last_error()
            logger.error(f"Không thể khởi tạo MT5!")
            if error:
                logger.error(f"  Mã lỗi: {error}")
                # Hiển thị chi tiết lỗi
                if hasattr(error, '_asdict'):
                    error_dict = error._asdict()
                    for key, value in error_dict.items():
                        logger.error(f"  {key}: {value}")
            logger.error("Giải pháp: Đảm bảo MetaTrader 5 đã được cài đặt trên máy")
            return False
        
        logger.info("MT5 đã được khởi tạo thành công!")
        
        # Đăng nhập
        logger.info(f"Đang đăng nhập với tài khoản {self.account}...")
        if not mt5.login(self.account, password=self.password, server=self.server):
            error = mt5.last_error()
            logger.error(f"Đăng nhập MT5 thất bại!")
            if error:
                logger.error(f"  Mã lỗi: {error}")
                if hasattr(error, '_asdict'):
                    error_dict = error._asdict()
                    for key, value in error_dict.items():
                        logger.error(f"  {key}: {value}")
            logger.error("Giải pháp:")
            logger.error("  1. Kiểm tra lại số tài khoản, mật khẩu, và tên server")
            logger.error("  2. Thử đăng nhập thủ công vào MT5 để xác nhận")
            logger.error(f"  3. Kiểm tra server name có đúng không: {self.server}")
            mt5.shutdown()
            return False
        
        logger.info("Đăng nhập thành công!")
        
        # Kiểm tra thông tin tài khoản
        account_info = mt5.account_info()
        if account_info is None:
            error = mt5.last_error()
            logger.error(f"Không thể lấy thông tin tài khoản!")
            if error:
                logger.error(f"  Mã lỗi: {error}")
            mt5.shutdown()
            return False
        
        self.connected = True
        logger.info(f"Đã kết nối Exness thành công!")
        logger.info(f"  Tài khoản: {account_info.login}")
        logger.info(f"  Server: {account_info.server}")
        logger.info(f"  Balance: {account_info.balance} {account_info.currency}")
        logger.info(f"  Leverage: 1:{account_info.leverage}")
        
        return True
    
    def disconnect(self):
        """Ngắt kết nối MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Đã ngắt kết nối MT5")
    
    def _convert_timeframe(self, timeframe: str) -> int:
        """
        Chuyển đổi timeframe từ string sang MT5 constant
        
        Parameters:
        -----------
        timeframe : str
            Khung thời gian (1m, 5m, 15m, 30m, 1h, 4h, 1d, etc.)
        
        Returns:
        --------
        int
            MT5 timeframe constant
        """
        timeframe_map = {
            '1m': mt5.TIMEFRAME_M1,
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '30m': mt5.TIMEFRAME_M30,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
            '1d': mt5.TIMEFRAME_D1,
            '1w': mt5.TIMEFRAME_W1,
            '1M': mt5.TIMEFRAME_MN1,
        }
        
        return timeframe_map.get(timeframe.lower(), mt5.TIMEFRAME_H1)
    
    def _convert_symbol(self, symbol: str) -> str:
        """
        Chuyển đổi symbol từ format chuẩn sang format MT5
        
        Parameters:
        -----------
        symbol : str
            Cặp tiền (VD: EUR/USD, GBP/USD)
        
        Returns:
        --------
        str
            Symbol MT5 (VD: EURUSD, GBPUSD)
        """
        # Exness thường dùng format không có dấu /
        return symbol.replace('/', '')
    
    def get_pip_value(self, symbol: str) -> float:
        """
        Lấy giá trị 1 pip cho symbol (Forex standard)
        
        Trong Forex:
        - 1 pip = 10 points cho hầu hết các cặp
        - Cặp có 3 hoặc 5 số thập phân: pip = point * 10
        - Cặp có 2 hoặc 4 số thập phân: pip = point
        
        Parameters:
        -----------
        symbol : str
            Symbol MT5 (VD: EURUSD)
        
        Returns:
        --------
        float
            Giá trị 1 pip trong giá:
            - 0.0001 cho EUR/USD (5 digits)
            - 0.01 cho USD/JPY (3 digits)
            - 0.0001 cho EUR/USD (4 digits, nếu có)
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            # Default: 4 số thập phân, 1 pip = 0.0001
            return 0.0001
        
        point = symbol_info.point
        digits = symbol_info.digits
        
        # Trong Forex, 1 pip thường = 10 points
        # Cặp có 3 hoặc 5 số thập phân: pip = 10 * point
        # Cặp có 2 hoặc 4 số thập phân: pip = point
        if digits == 3 or digits == 5:
            # 5 digits: EUR/USD = 1.23456, point = 0.00001, pip = 0.0001
            # 3 digits: USD/JPY = 154.089, point = 0.001, pip = 0.01
            pip_value = point * 10
        elif digits == 2 or digits == 4:
            # 4 digits: EUR/USD (cũ) = 1.2345, point = 0.0001, pip = 0.0001
            # 2 digits: USD/JPY (cũ) = 154.08, point = 0.01, pip = 0.01
            pip_value = point
        else:
            # Fallback: giả sử pip = 10 * point (phổ biến nhất)
            pip_value = point * 10
        
        return pip_value
    
    def _get_filling_mode(self, symbol: str) -> int:
        """
        Lấy filling mode được hỗ trợ cho symbol
        
        Parameters:
        -----------
        symbol : str
            Symbol MT5 (VD: EURUSD)
        
        Returns:
        --------
        int
            Filling mode constant (ORDER_FILLING_FOK, ORDER_FILLING_IOC, hoặc ORDER_FILLING_RETURN)
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            # Default: thử FOK trước (phổ biến nhất với Forex)
            return mt5.ORDER_FILLING_FOK
        
        # Kiểm tra filling modes được hỗ trợ
        # filling_mode là bitmask:
        # - Bit 0 (value 1) = FOK support
        # - Bit 1 (value 2) = IOC support  
        # - Bit 2 (value 4) = RETURN support
        filling_modes = symbol_info.filling_mode
        
        # Thử theo thứ tự ưu tiên: FOK -> IOC -> RETURN
        # Sử dụng bitwise AND để kiểm tra từng bit
        if filling_modes & 1:  # Bit 0 = FOK supported
            logger.debug(f"Symbol {symbol} hỗ trợ FOK (filling_mode={filling_modes})")
            return mt5.ORDER_FILLING_FOK
        elif filling_modes & 2:  # Bit 1 = IOC supported
            logger.debug(f"Symbol {symbol} hỗ trợ IOC (filling_mode={filling_modes})")
            return mt5.ORDER_FILLING_IOC
        elif filling_modes & 4:  # Bit 2 = RETURN supported
            logger.debug(f"Symbol {symbol} hỗ trợ RETURN (filling_mode={filling_modes})")
            return mt5.ORDER_FILLING_RETURN
        else:
            # Fallback: dùng FOK (phổ biến nhất với Forex)
            logger.warning(f"Không xác định filling mode cho {symbol} (filling_mode={filling_modes}), dùng FOK")
            return mt5.ORDER_FILLING_FOK
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> pd.DataFrame:
        """
        Lấy dữ liệu OHLCV từ MT5
        
        Parameters:
        -----------
        symbol : str
            Cặp tiền (VD: EUR/USD)
        timeframe : str
            Khung thời gian
        limit : int
            Số lượng nến cần lấy
        
        Returns:
        --------
        pandas.DataFrame
            DataFrame chứa dữ liệu OHLCV
        """
        if not self.connected:
            logger.error("Chưa kết nối MT5")
            return pd.DataFrame()
        
        try:
            mt5_symbol = self._convert_symbol(symbol)
            mt5_timeframe = self._convert_timeframe(timeframe)
            
            # Kiểm tra symbol có tồn tại không
            symbol_info = mt5.symbol_info(mt5_symbol)
            if symbol_info is None:
                logger.error(f"Symbol {mt5_symbol} không tồn tại. Thử {symbol}...")
                # Thử với symbol gốc
                mt5_symbol = symbol.replace('/', '')
                symbol_info = mt5.symbol_info(mt5_symbol)
                if symbol_info is None:
                    logger.error(f"Symbol {mt5_symbol} không tìm thấy")
                    return pd.DataFrame()
            
            # Nếu symbol chưa được hiển thị, thêm vào Market Watch
            if not symbol_info.visible:
                if not mt5.symbol_select(mt5_symbol, True):
                    logger.error(f"Không thể thêm {mt5_symbol} vào Market Watch")
                    return pd.DataFrame()
            
            # Lấy dữ liệu
            rates = mt5.copy_rates_from_pos(mt5_symbol, mt5_timeframe, 0, limit)
            
            if rates is None or len(rates) == 0:
                logger.error(f"Không lấy được dữ liệu cho {mt5_symbol}: {mt5.last_error()}")
                return pd.DataFrame()
            
            # ✅ BỎ QUA NẾN ĐẦU TIÊN (nến 0 - đang hình thành, chưa đóng)
            # Chỉ dùng nến đã đóng để tính indicators chính xác
            if len(rates) > 1:
                rates = rates[1:]  # Bỏ nến 0 (đang hình thành), chỉ dùng nến đã đóng
            elif len(rates) == 1:
                # Nếu chỉ có 1 nến (đang hình thành), không có nến đã đóng
                logger.warning(f"Chỉ có nến đang hình thành cho {mt5_symbol}, cần đợi nến đóng")
                return pd.DataFrame()
            
            # Chuyển đổi sang DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.rename(columns={
                'time': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            }, inplace=True)
            
            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu OHLCV cho {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Lấy giá hiện tại
        
        Parameters:
        -----------
        symbol : str
            Cặp tiền
        
        Returns:
        --------
        float hoặc None
            Giá hiện tại (bid)
        """
        if not self.connected:
            return None
        
        try:
            mt5_symbol = self._convert_symbol(symbol)
            tick = mt5.symbol_info_tick(mt5_symbol)
            
            if tick is None:
                return None
            
            return tick.bid  # Giá bid (giá bán)
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá cho {symbol}: {e}")
            return None
    
    def get_balance(self) -> Optional[float]:
        """
        Lấy số dư tài khoản
        
        Returns:
        --------
        float hoặc None
            Số dư tài khoản
        """
        if not self.connected:
            return None
        
        account_info = mt5.account_info()
        if account_info is None:
            return None
        
        return account_info.balance
    
    def create_market_order(self, symbol: str, action: str, volume: float, 
                           stop_loss: float = None, take_profit: float = None) -> Optional[int]:
        """
        Đặt lệnh thị trường
        
        Parameters:
        -----------
        symbol : str
            Cặp tiền
        action : str
            'buy' hoặc 'sell'
        volume : float
            Khối lượng (lot)
        stop_loss : float
            Giá Stop Loss (optional)
        take_profit : float
            Giá Take Profit (optional)
        
        Returns:
        --------
        int hoặc None
            Ticket của lệnh nếu thành công
        """
        if not self.connected:
            logger.error("Chưa kết nối MT5")
            return None
        
        try:
            mt5_symbol = self._convert_symbol(symbol)
            
            # Lấy thông tin symbol
            symbol_info = mt5.symbol_info(mt5_symbol)
            if symbol_info is None:
                logger.error(f"Symbol {mt5_symbol} không tìm thấy")
                return None
            
            # Xác định loại lệnh
            if action.lower() == 'buy':
                order_type = mt5.ORDER_TYPE_BUY
                tick = mt5.symbol_info_tick(mt5_symbol)
                if tick is None:
                    logger.error(f"Không lấy được giá tick cho {mt5_symbol}")
                    return None
                price = tick.ask
            elif action.lower() == 'sell':
                order_type = mt5.ORDER_TYPE_SELL
                tick = mt5.symbol_info_tick(mt5_symbol)
                if tick is None:
                    logger.error(f"Không lấy được giá tick cho {mt5_symbol}")
                    return None
                price = tick.bid
            else:
                logger.error(f"Action không hợp lệ: {action}")
                return None
            
            # Lấy filling mode được hỗ trợ cho symbol này
            filling_mode = self._get_filling_mode(mt5_symbol)
            
            # Tạo request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": mt5_symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Ichimoku+BBand Bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            
            filling_mode_name = "FOK" if filling_mode == mt5.ORDER_FILLING_FOK else "IOC" if filling_mode == mt5.ORDER_FILLING_IOC else "RETURN"
            logger.debug(f"Filling mode cho {symbol}: {filling_mode_name} (filling_mode={filling_mode})")
            
            # Thêm Stop Loss và Take Profit
            if stop_loss is not None:
                request["sl"] = stop_loss
            if take_profit is not None:
                request["tp"] = take_profit
            
            # Gửi lệnh
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Lỗi đặt lệnh {action} {symbol}: {result.retcode}, {result.comment}")
                return None
            
            logger.info(f"Đặt lệnh {action} {symbol} thành công: Ticket={result.order}, Volume={volume}")
            return result.order
            
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh {action} cho {symbol}: {e}")
            return None
    
    def close_position(self, ticket: int) -> bool:
        """
        Đóng một position bằng ticket
        
        Parameters:
        -----------
        ticket : int
            Ticket của position
        
        Returns:
        --------
        bool
            True nếu thành công
        """
        if not self.connected:
            return False
        
        try:
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                logger.error(f"Không tìm thấy position với ticket {ticket}")
                return False
            
            position = position[0]
            mt5_symbol = position.symbol
            
            # Xác định loại lệnh đóng (ngược với lệnh mở)
            if position.type == mt5.ORDER_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                tick = mt5.symbol_info_tick(mt5_symbol)
                if tick is None:
                    logger.error(f"Không lấy được giá tick cho {mt5_symbol}")
                    return False
                price = tick.bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                tick = mt5.symbol_info_tick(mt5_symbol)
                if tick is None:
                    logger.error(f"Không lấy được giá tick cho {mt5_symbol}")
                    return False
                price = tick.ask
            
            # Lấy filling mode được hỗ trợ cho symbol này
            filling_mode = self._get_filling_mode(mt5_symbol)
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": mt5_symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Lỗi đóng position {ticket}: {result.retcode}, {result.comment}")
                return False
            
            logger.info(f"Đã đóng position {ticket} thành công")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi đóng position {ticket}: {e}")
            return False
    
    def get_positions(self, symbol: str = None) -> List[Dict]:
        """
        Lấy danh sách positions
        
        Parameters:
        -----------
        symbol : str
            Lọc theo symbol (optional)
        
        Returns:
        --------
        list
            Danh sách positions
        """
        if not self.connected:
            return []
        
        try:
            if symbol:
                mt5_symbol = self._convert_symbol(symbol)
                positions = mt5.positions_get(symbol=mt5_symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'buy' if pos.type == mt5.ORDER_TYPE_BUY else 'sell',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'time': datetime.fromtimestamp(pos.time)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy positions: {e}")
            return []

