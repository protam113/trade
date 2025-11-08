"""
MACD Trading Bot
Sử dụng Moving Average Convergence Divergence (MACD) để trading
"""
import pandas as pd
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging
import sys
import os
import io

# Thêm path của project root để import exness_connector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_macd import (
    EXCHANGE_NAME, EXCHANGE_API_KEY, EXCHANGE_API_SECRET,
    SYMBOLS, MAX_POSITION_SIZE, STOP_LOSS_PIPS, TAKE_PROFIT_PIPS,
    USE_SANDBOX, MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER, LOT_SIZE,
    TIMEFRAMES, TIMEFRAME_WEIGHTS, PRIMARY_TIMEFRAME,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL, USE_TALIB,
    MIN_CONFIDENCE, MIN_BULLISH_SCORE, MIN_BEARISH_SCORE
)

from macd_indicator import calculate_macd, get_macd_signals
from exness_connector import ExnessConnector

# Setup logging với encoding UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Lấy đường dẫn thư mục chứa file này (bot_macd/)
bot_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(bot_dir, 'macd_bot.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MACDBot:
    def __init__(self):
        """Khởi tạo MACD Trading Bot"""
        self.exchange_type = EXCHANGE_NAME.lower()
        self.exchange = None
        self.exness_connector = None
        self._initialize_exchange()
        self.open_positions = {}
        
    def _initialize_exchange(self):
        """Khởi tạo kết nối với exchange"""
        if self.exchange_type == "exness":
            logger.info("Đang kết nối với Exness qua MetaTrader 5...")
            self.exness_connector = ExnessConnector(
                account=MT5_ACCOUNT,
                password=MT5_PASSWORD,
                server=MT5_SERVER
            )
            if not self.exness_connector.connect():
                raise Exception("Không thể kết nối với Exness MT5")
            logger.info("Đã kết nối Exness thành công!")
        else:
            try:
                import ccxt
            except ImportError:
                raise Exception("CCXT chưa được cài đặt. Hãy chạy: pip install ccxt")
            
            exchange_class = getattr(ccxt, EXCHANGE_NAME)
            
            config = {
                'apiKey': EXCHANGE_API_KEY,
                'secret': EXCHANGE_API_SECRET,
                'enableRateLimit': True,
            }
            
            if USE_SANDBOX:
                config['sandbox'] = True
                logger.info("Chế độ SANDBOX được bật")
            
            self.exchange = exchange_class(config)
            logger.info(f"Đã kết nối với {EXCHANGE_NAME}")
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = PRIMARY_TIMEFRAME, limit: int = 200) -> pd.DataFrame:
        """
        Lấy dữ liệu OHLCV từ exchange
        
        Parameters:
        -----------
        symbol : str
            Cặp tiền
        timeframe : str
            Khung thời gian
        limit : int
            Số lượng nến cần lấy
        
        Returns:
        --------
        pandas.DataFrame
            DataFrame chứa dữ liệu OHLCV
        """
        try:
            if self.exchange_type == "exness":
                return self.exness_connector.fetch_ohlcv(symbol, timeframe, limit)
            else:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu OHLCV cho {symbol}: {e}")
            return pd.DataFrame()
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """
        Phân tích một cặp tiền với MACD trên nhiều timeframe
        
        Parameters:
        -----------
        symbol : str
            Cặp tiền cần phân tích
        
        Returns:
        --------
        dict
            Dictionary chứa kết quả phân tích
        """
        logger.info(f"Đang phân tích {symbol} với MACD trên {len(TIMEFRAMES)} timeframe...")
        
        # Phân tích trên tất cả các timeframe
        timeframe_analyses = {}
        all_bullish_scores = []
        all_bearish_scores = []
        
        for tf in TIMEFRAMES:
            try:
                # Lấy dữ liệu cho timeframe này
                df = self.fetch_ohlcv(symbol, timeframe=tf)
                if df.empty:
                    logger.warning(f"Không lấy được dữ liệu cho {symbol} trên {tf}")
                    continue
                
                # Tính toán MACD
                macd_df = calculate_macd(
                    df['close'],
                    fast=MACD_FAST,
                    slow=MACD_SLOW,
                    signal=MACD_SIGNAL,
                    talib=USE_TALIB
                )
                
                if macd_df.empty:
                    logger.warning(f"Không tính được MACD cho {symbol} trên {tf}")
                    continue
                
                # Phân tích tín hiệu MACD
                macd_signals = get_macd_signals(df, macd_df)
                
                # Lưu kết quả
                timeframe_analyses[tf] = {
                    'macd': macd_signals,
                    'macd_df': macd_df
                }
                
                # Tính điểm có trọng số
                weight = TIMEFRAME_WEIGHTS.get(tf, 10) / 100.0
                weighted_bullish = macd_signals['bullish_score'] * weight
                weighted_bearish = macd_signals['bearish_score'] * weight
                
                all_bullish_scores.append(weighted_bullish)
                all_bearish_scores.append(weighted_bearish)
                
                logger.debug(f"{symbol} {tf}: Bullish={macd_signals['bullish_score']:.1f} (x{weight:.2f}), "
                           f"Bearish={macd_signals['bearish_score']:.1f} (x{weight:.2f})")
                
            except Exception as e:
                logger.error(f"Lỗi khi phân tích {symbol} trên {tf}: {e}")
                continue
        
        if not timeframe_analyses:
            return {'error': 'Không lấy được dữ liệu từ bất kỳ timeframe nào'}
        
        # Kết hợp tín hiệu từ tất cả timeframe (có trọng số)
        total_bullish_score = sum(all_bullish_scores)
        total_bearish_score = sum(all_bearish_scores)
        
        # Quyết định action dựa trên điểm tổng hợp
        action = 'hold'
        confidence = 0
        reasons = []
        
        if total_bullish_score >= MIN_BULLISH_SCORE and total_bullish_score > total_bearish_score:
            action = 'buy'
            confidence = min(total_bullish_score / 10.0, 1.0)
            reasons.append(f"Multi-TF MACD Bullish Score: {total_bullish_score:.2f}")
        elif total_bearish_score >= MIN_BEARISH_SCORE and total_bearish_score > total_bullish_score:
            action = 'sell'
            confidence = min(total_bearish_score / 10.0, 1.0)
            reasons.append(f"Multi-TF MACD Bearish Score: {total_bearish_score:.2f}")
        else:
            reasons.append(f"Scores too low (Bull:{total_bullish_score:.2f}, Bear:{total_bearish_score:.2f})")
        
        # Lấy giá từ primary timeframe
        if self.exchange_type == "exness":
            current_price = self.exness_connector.get_current_price(symbol)
            if current_price is None:
                primary_df = self.fetch_ohlcv(symbol, timeframe=PRIMARY_TIMEFRAME)
                if not primary_df.empty:
                    current_price = float(primary_df['close'].iloc[-1])
                else:
                    logger.warning(f"Không lấy được giá cho {symbol}")
                    current_price = 0
        else:
            primary_df = self.fetch_ohlcv(symbol, timeframe=PRIMARY_TIMEFRAME)
            if primary_df.empty:
                primary_df = self.fetch_ohlcv(symbol, timeframe=TIMEFRAMES[0])
            current_price = float(primary_df['close'].iloc[-1]) if not primary_df.empty else 0
        
        # Lấy tín hiệu từ primary timeframe để hiển thị
        primary_analysis = timeframe_analyses.get(PRIMARY_TIMEFRAME, {})
        primary_macd = primary_analysis.get('macd', {})
        
        combined_signal = {
            'action': action,
            'confidence': confidence,
            'bullish_score': total_bullish_score,
            'bearish_score': total_bearish_score,
            'reason': reasons,
            'timeframe_scores': {tf: {
                'bullish': timeframe_analyses[tf]['macd']['bullish_score'],
                'bearish': timeframe_analyses[tf]['macd']['bearish_score']
            } for tf in timeframe_analyses.keys()}
        }
        
        analysis = {
            'symbol': symbol,
            'current_price': current_price,
            'macd': primary_macd,
            'combined_signal': combined_signal,
            'timeframe_analyses': timeframe_analyses,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"{symbol} - Multi-TF MACD Signal: {action} (Conf:{confidence:.2f}), "
                   f"Bullish:{total_bullish_score:.1f}, Bearish:{total_bearish_score:.1f}")
        
        return analysis
    
    def execute_trade(self, symbol: str, action: str, price: float, confidence: float):
        """
        Thực hiện lệnh giao dịch
        
        Parameters:
        -----------
        symbol : str
            Cặp tiền
        action : str
            'buy' hoặc 'sell'
        price : float
            Giá hiện tại
        confidence : float
            Độ tin cậy của tín hiệu (0-1)
        """
        if confidence < MIN_CONFIDENCE:
            logger.info(f"{symbol}: Confidence quá thấp ({confidence:.2f}), bỏ qua")
            return
        
        try:
            if self.exchange_type == "exness":
                self._execute_exness_trade(symbol, action, price, confidence)
            else:
                self._execute_ccxt_trade(symbol, action, price, confidence)
                
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện lệnh {action} cho {symbol}: {e}")
    
    def _execute_exness_trade(self, symbol: str, action: str, price: float, confidence: float):
        """Thực hiện lệnh với Exness"""
        if action == 'buy':
            # Kiểm tra xem đã có position chưa
            positions = self.exness_connector.get_positions(symbol)
            if positions:
                has_long = any(pos['type'] == 'buy' for pos in positions)
                has_short = any(pos['type'] == 'sell' for pos in positions)
                
                if has_long:
                    logger.info(f"{symbol}: Đã có LONG position, signal vẫn là BUY → Giữ nguyên")
                    return
                elif has_short:
                    logger.info(f"{symbol}: Đã có SHORT position, signal là BUY → Đóng short, mở long")
                    for pos in positions:
                        if pos['type'] == 'sell':
                            if self.exness_connector.close_position(pos['ticket']):
                                pnl = pos['profit']
                                logger.info(f"Đóng SHORT position {symbol}: P&L = {pnl:.2f}")
                                if symbol in self.open_positions:
                                    del self.open_positions[symbol]
            
            # Tính toán lot size
            lot_size = min(MAX_POSITION_SIZE, LOT_SIZE)
            
            # Tính SL/TP theo pip
            mt5_symbol = self.exness_connector._convert_symbol(symbol)
            pip_value = self.exness_connector.get_pip_value(mt5_symbol)
            
            stop_loss_price = price - (STOP_LOSS_PIPS * pip_value)
            take_profit_price = price + (TAKE_PROFIT_PIPS * pip_value)
            
            logger.info(f"Đặt lệnh MUA {symbol}: {lot_size} lot @ {price:.5f}")
            logger.info(f"  SL: {stop_loss_price:.5f} ({STOP_LOSS_PIPS} pip), TP: {take_profit_price:.5f} ({TAKE_PROFIT_PIPS} pip)")
            
            ticket = self.exness_connector.create_market_order(
                symbol=symbol,
                action='buy',
                volume=lot_size,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
            
            if ticket:
                self.open_positions[symbol] = {
                    'ticket': ticket,
                    'side': 'long',
                    'entry_price': price,
                    'lot_size': lot_size,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'timestamp': datetime.now()
                }
            else:
                logger.warning(f"Không thể đặt lệnh mua {symbol}")
                
        elif action == 'sell':
            positions = self.exness_connector.get_positions(symbol)
            if positions:
                has_long = any(pos['type'] == 'buy' for pos in positions)
                has_short = any(pos['type'] == 'sell' for pos in positions)
                
                if has_short:
                    logger.info(f"{symbol}: Đã có SHORT position, signal vẫn là SELL → Giữ nguyên")
                    return
                elif has_long:
                    logger.info(f"{symbol}: Đã có LONG position, signal là SELL → Đóng long, mở short")
                    for pos in positions:
                        if pos['type'] == 'buy':
                            if self.exness_connector.close_position(pos['ticket']):
                                pnl = pos['profit']
                                logger.info(f"Đóng LONG position {symbol}: P&L = {pnl:.2f}")
                                if symbol in self.open_positions:
                                    del self.open_positions[symbol]
            
            # Tính toán lot size
            lot_size = min(MAX_POSITION_SIZE, LOT_SIZE)
            
            # Tính SL/TP theo pip (ngược lại với BUY)
            mt5_symbol = self.exness_connector._convert_symbol(symbol)
            pip_value = self.exness_connector.get_pip_value(mt5_symbol)
            
            stop_loss_price = price + (STOP_LOSS_PIPS * pip_value)
            take_profit_price = price - (TAKE_PROFIT_PIPS * pip_value)
            
            logger.info(f"Đặt lệnh BÁN (SHORT) {symbol}: {lot_size} lot @ {price:.5f}")
            logger.info(f"  SL: {stop_loss_price:.5f} ({STOP_LOSS_PIPS} pip), TP: {take_profit_price:.5f} ({TAKE_PROFIT_PIPS} pip)")
            
            ticket = self.exness_connector.create_market_order(
                symbol=symbol,
                action='sell',
                volume=lot_size,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
            
            if ticket:
                self.open_positions[symbol] = {
                    'ticket': ticket,
                    'side': 'short',
                    'entry_price': price,
                    'lot_size': lot_size,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'timestamp': datetime.now()
                }
            else:
                logger.warning(f"Không thể đặt lệnh bán (short) {symbol}")
    
    def _execute_ccxt_trade(self, symbol: str, action: str, price: float, confidence: float):
        """Thực hiện lệnh với CCXT exchange"""
        if action == 'buy':
            available_balance = 100
            amount = min(MAX_POSITION_SIZE, available_balance / price)
            
            logger.info(f"Đặt lệnh MUA {symbol}: {amount:.6f} @ {price:.2f}")
            # Uncomment để thực hiện lệnh thật:
            # order = self.exchange.create_market_buy_order(symbol, amount)
            
            self.open_positions[symbol] = {
                'side': 'long',
                'entry_price': price,
                'amount': amount,
                'stop_loss': price * 0.98,
                'take_profit': price * 1.04,
                'timestamp': datetime.now()
            }
            
        elif action == 'sell':
            if symbol in self.open_positions:
                position = self.open_positions[symbol]
                amount = position['amount']
                
                logger.info(f"Đặt lệnh BÁN {symbol}: {amount:.6f} @ {price:.2f}")
                # Uncomment để thực hiện lệnh thật:
                # order = self.exchange.create_market_sell_order(symbol, amount)
                
                if position['side'] == 'long':
                    pnl = (price - position['entry_price']) * amount
                    pnl_percent = ((price - position['entry_price']) / position['entry_price']) * 100
                    logger.info(f"Đóng position: P&L = {pnl:.2f} USDT ({pnl_percent:.2f}%)")
                
                del self.open_positions[symbol]
            else:
                logger.info(f"{symbol}: Không có position để đóng")
    
    def check_stop_loss_take_profit(self, symbol: str, current_price: float):
        """
        Kiểm tra và thực hiện Stop Loss / Take Profit
        """
        if self.exchange_type == "exness":
            positions = self.exness_connector.get_positions(symbol)
            if not positions and symbol in self.open_positions:
                logger.info(f"{symbol}: Position đã được đóng (có thể do SL/TP)")
                del self.open_positions[symbol]
        else:
            if symbol not in self.open_positions:
                return
            
            position = self.open_positions[symbol]
            
            if position['side'] == 'long':
                if current_price <= position['stop_loss']:
                    logger.warning(f"{symbol}: Stop Loss triggered @ {current_price:.2f}")
                    self.execute_trade(symbol, 'sell', current_price, 1.0)
                elif current_price >= position['take_profit']:
                    logger.info(f"{symbol}: Take Profit triggered @ {current_price:.2f}")
                    self.execute_trade(symbol, 'sell', current_price, 1.0)
    
    def run(self):
        """Chạy bot trading"""
        logger.info("=== MACD TRADING BOT BẮT ĐẦU ===")
        
        while True:
            try:
                for symbol in SYMBOLS:
                    # Phân tích
                    analysis = self.analyze_symbol(symbol)
                    
                    if 'error' in analysis:
                        continue
                    
                    # Kiểm tra Stop Loss / Take Profit
                    self.check_stop_loss_take_profit(symbol, analysis['current_price'])
                    
                    # Thực hiện giao dịch nếu có tín hiệu
                    signal = analysis['combined_signal']
                    if signal['action'] in ['buy', 'sell']:
                        self.execute_trade(
                            symbol,
                            signal['action'],
                            analysis['current_price'],
                            signal['confidence']
                        )
                
                # Đợi một chu kỳ trước khi phân tích lại
                wait_time = 60
                if PRIMARY_TIMEFRAME == "1m":
                    wait_time = 60
                elif PRIMARY_TIMEFRAME == "5m":
                    wait_time = 300
                elif PRIMARY_TIMEFRAME == "15m":
                    wait_time = 900
                elif PRIMARY_TIMEFRAME == "1h":
                    wait_time = 3600
                
                logger.info(f"Đợi {wait_time}s trước khi phân tích lại (Primary TF: {PRIMARY_TIMEFRAME})...")
                time.sleep(wait_time)
                
            except KeyboardInterrupt:
                logger.info("Bot được dừng bởi người dùng")
                break
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp chính: {e}")
                time.sleep(60)


if __name__ == "__main__":
    bot = MACDBot()
    bot.run()

