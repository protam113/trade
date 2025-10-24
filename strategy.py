"""
strategy.py - Trading Strategy Logic
Chứa các điều kiện entry/exit và tính toán SL/TP
"""

class TrendFollowingSellStrategy:
    def __init__(self, config):
        """
        Initialize strategy với config parameters
        
        Args:
            config (dict): Dictionary chứa các tham số:
                - spread: float
                - atr_sl_multiplier: float
                - atr_tp_multiplier: float
                - anti_whipsaw_bars: int
        """
        self.spread = config.get('spread', 0.00015)
        self.atr_sl_multiplier = config.get('atr_sl_multiplier', 1.5)
        self.atr_tp_multiplier = config.get('atr_tp_multiplier', 2.5)
        self.anti_whipsaw_bars = config.get('anti_whipsaw_bars', 2)
        self.lot = config.get('lot', 0.1)
        
        self.position = None
        self.last_entry_bars = 0
        
    def check_entry_signal(self, indicators):
        """
        Kiểm tra điều kiện vào lệnh SELL
        
        Args:
            indicators (dict): Dictionary chứa các indicators hiện tại:
                - ema8, ema21, ema50
                - price, vwap
                - rsi, macd_hist
                - atr
                
        Returns:
            tuple: (bool, dict) - (có signal không, thông tin entry)
        """
        self.last_entry_bars += 1
        
        # Không có position và đã đợi đủ bars
        if self.position is not None or self.last_entry_bars < self.anti_whipsaw_bars:
            return False, None
        
        # Lấy indicators
        ema8 = indicators['ema8']
        ema21 = indicators['ema21']
        ema50 = indicators['ema50']
        price = indicators['price']
        vwap = indicators['vwap']
        rsi = indicators['rsi']
        macd_hist = indicators['macd_hist']
        atr = indicators['atr']
        
        # === SELL CONDITIONS ===
        cond1 = ema8 < ema21  # Downtrend
        cond2 = price < ema8  # Price below fast MA
        cond3 = price < vwap if vwap is not None else True  # Below VWAP
        cond4 = rsi < 50  # Bearish momentum
        cond5 = macd_hist < 0  # MACD bearish
        
        sell_signal = cond1 and cond2 and cond3 and cond4 and cond5
        
        # Debug info
        conditions_met = sum([cond1, cond2, cond3, cond4, cond5])
        debug_info = {
            'conditions_met': conditions_met,
            'cond1_ema8_below_ema21': cond1,
            'cond2_price_below_ema8': cond2,
            'cond3_price_below_vwap': cond3,
            'cond4_rsi_below_50': cond4,
            'cond5_macd_negative': cond5
        }
        
        if sell_signal:
            # Tính toán entry, SL, TP
            entry_price = price
            sl_distance = self.atr_sl_multiplier * atr
            tp_distance = self.atr_tp_multiplier * atr
            
            entry_info = {
                'type': 'sell',
                'entry': entry_price,
                'sl': entry_price + sl_distance,
                'tp': entry_price - tp_distance,
                'atr': atr
            }
            
            self.position = entry_info.copy()
            self.last_entry_bars = 0
            
            return True, entry_info
        
        return False, debug_info
    
    def check_exit_signal(self, current_data):
        """
        Kiểm tra điều kiện thoát lệnh
        
        Args:
            current_data (dict): Dữ liệu bar hiện tại:
                - high, low, close
                - ema8, ema21
                - ema8_prev, ema21_prev
                
        Returns:
            tuple: (bool, str, float, float) - (có exit không, lý do, giá exit, profit)
        """
        if self.position is None:
            return False, None, None, None
        
        high = current_data['high']
        low = current_data['low']
        close = current_data['close']
        ema8 = current_data['ema8']
        ema21 = current_data['ema21']
        ema8_prev = current_data['ema8_prev']
        ema21_prev = current_data['ema21_prev']
        
        exit_price = None
        reason = None
        
        if self.position['type'] == 'sell':
            # TP hit
            if low <= self.position['tp']:
                exit_price = self.position['tp']
                reason = 'TP✅'
            # SL hit
            elif high >= self.position['sl']:
                exit_price = self.position['sl']
                reason = 'SL❌'
            # Trend reversal: EMA8 crosses above EMA21
            elif ema8_prev <= ema21_prev and ema8 > ema21:
                exit_price = close
                reason = 'REVERSAL🔄'
        
        if exit_price is not None:
            # Tính profit
            profit = (self.position['entry'] - exit_price - self.spread) * self.lot * 100000
            pips = (self.position['entry'] - exit_price) / 0.0001
            
            self.position = None
            self.last_entry_bars = 0
            
            return True, reason, exit_price, profit
        
        return False, None, None, None
    
    def reset(self):
        """Reset strategy state"""
        self.position = None
        self.last_entry_bars = 0
    
    def get_position(self):
        """Get current position"""
        return self.position
    
    def get_debug_status(self, indicators):
        """
        Get debug status string cho UI
        
        Args:
            indicators (dict): Current indicators
            
        Returns:
            str: Status string
        """
        if self.position is not None:
            return "🎯 IN POSITION"
        
        _, debug_info = self.check_entry_signal(indicators)
        
        if isinstance(debug_info, dict) and 'conditions_met' in debug_info:
            conditions = debug_info['conditions_met']
            status = f"📊 Conditions: {conditions}/5 | "
            status += f"EMA8<21: {'✅' if debug_info['cond1_ema8_below_ema21'] else '❌'} | "
            status += f"P<EMA8: {'✅' if debug_info['cond2_price_below_ema8'] else '❌'} | "
            status += f"P<VWAP: {'✅' if debug_info['cond3_price_below_vwap'] else '❌'} | "
            status += f"RSI<50: {'✅' if debug_info['cond4_rsi_below_50'] else '❌'} | "
            status += f"MACD<0: {'✅' if debug_info['cond5_macd_negative'] else '❌'}"
            return status
        
        return "📊 Waiting for setup..."