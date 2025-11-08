from ...lib.symbol import Symbol


class CryptoSymbol(Symbol):
    """
    Subclass of Symbol for Crypto Symbols. 
    Handles the conversion of cryptocurrency and the computation of stop loss,
    take profit and volume for crypto trading.
    
    Key differences from Forex:
    - No pip concept (uses point directly)
    - Different contract size calculation
    - Price precision varies greatly (BTC vs altcoins)
    - Supports both USDT and BTC pairs
    """

    @property
    def pip(self):
        """
        Returns the point value for crypto symbols.
        For crypto, pip = point (no 10x multiplier like forex)

        Returns:
            float: The point value of the symbol.
        """
        return self.point

    @property
    def tick_size(self):
        """
        Returns the minimum price movement (tick size) for the symbol.
        This is especially important for crypto due to varying price levels.
        
        Returns:
            float: The tick size of the symbol.
        """
        return self.point

    def compute_points(self, *, amount: float, volume: float) -> float:
        """
        Compute the number of points required for a trade.
        Given the amount and the volume of the trade.

        Args:
            amount (float): Amount to trade (in quote currency, e.g., USDT)
            volume (float): Volume to trade (in base currency, e.g., BTC)

        Returns:
            float: Number of points required
            
        Example:
            For BTCUSDT: amount=100 USDT, volume=0.01 BTC
            -> points = how much BTC needs to move in points
        """
        if volume == 0:
            return 0
        points = amount / (volume * self.point * self.trade_contract_size)
        return points

    async def compute_volume_points(self, *, amount: float, points: float, round_down: bool = False) -> float:
        """
        Compute the volume required for a trade.
        Given the amount and the number of points.

        Args:
            amount (float): Amount to trade (in quote currency)
            points (float): Number of points for the trade
            round_down (bool): Round down the computed volume to the nearest step (default False)

        Returns:
            float: The volume required for the trade
            
        Example:
            For BTCUSDT with 100 USDT risk and 1000 point SL:
            -> volume = 100 / (0.01 * 1000 * 1) = 10 BTC (will be rounded)
        """
        if points == 0:
            return self.volume_min
            
        volume = amount / (self.point * points * self.trade_contract_size)
        return self.round_off_volume(volume=volume, round_down=round_down)

    async def compute_volume_sl(self, *, amount: float, price: float, sl: float, round_down: bool = False) -> float:
        """
        Compute the volume required for a trade.
        Given the amount, the entry price and the stop loss.

        Args:
            amount (float): Amount to trade (risk amount in quote currency)
            price (float): The entry price of the trade
            sl (float): The stop loss price of the trade
            round_down (bool): Round down the computed volume to the nearest step (default False)

        Returns:
            float: The volume required for the trade
            
        Example:
            For BTCUSDT:
            - amount = 100 USDT (max risk)
            - price = 50000 USDT
            - sl = 49000 USDT
            -> volume = 100 / (|50000-49000| * 1) = 0.1 BTC
        """
        price_diff = abs(price - sl)
        if price_diff == 0:
            return self.volume_min
            
        volume = amount / (price_diff * self.trade_contract_size)
        return self.round_off_volume(volume=volume, round_down=round_down)

    async def compute_volume_percent(self, *, balance: float, risk_percent: float, price: float, sl: float, 
                                     round_down: bool = False) -> float:
        """
        Compute volume based on risk percentage of account balance.
        Common for crypto trading with risk management.
        
        Args:
            balance (float): Account balance (in quote currency, e.g., USDT)
            risk_percent (float): Risk percentage per trade (e.g., 2.0 for 2%)
            price (float): Entry price
            sl (float): Stop loss price
            round_down (bool): Round down the volume (default False)
            
        Returns:
            float: The volume required for the trade
            
        Example:
            - balance = 10000 USDT
            - risk_percent = 2.0 (2%)
            - price = 50000, sl = 49000
            -> risk_amount = 200 USDT
            -> volume = 200 / 1000 = 0.2 BTC
        """
        risk_amount = balance * (risk_percent / 100)
        return await self.compute_volume_sl(
            amount=risk_amount,
            price=price,
            sl=sl,
            round_down=round_down
        )

    def compute_pip_value(self, *, volume: float, quote_currency_rate: float = 1.0) -> float:
        """
        Compute the value of one point movement for the given volume.
        Useful for risk calculation.
        
        Args:
            volume (float): Trading volume
            quote_currency_rate (float): Exchange rate to account currency (default 1.0)
            
        Returns:
            float: Value per point movement
            
        Example:
            For BTCUSDT with volume=0.1:
            -> pip_value = 0.1 * 0.01 * 1 = 0.001 USDT per point
        """
        return volume * self.point * self.trade_contract_size * quote_currency_rate

    def compute_profit_loss(self, *, entry_price: float, exit_price: float, volume: float, 
                           is_long: bool = True) -> float:
        """
        Calculate profit/loss for a trade.
        
        Args:
            entry_price (float): Entry price
            exit_price (float): Exit price
            volume (float): Trading volume
            is_long (bool): True for long position, False for short
            
        Returns:
            float: Profit/loss in quote currency
            
        Example:
            Long BTCUSDT:
            - entry = 50000, exit = 51000, volume = 0.1
            -> P/L = (51000 - 50000) * 0.1 = 100 USDT
        """
        price_diff = exit_price - entry_price if is_long else entry_price - exit_price
        return price_diff * volume * self.trade_contract_size

    def compute_risk_reward_ratio(self, *, price: float, tp: float, sl: float) -> float:
        """
        Calculate risk-reward ratio for a trade setup.
        
        Args:
            price (float): Entry price
            tp (float): Take profit price
            sl (float): Stop loss price
            
        Returns:
            float: Risk-reward ratio (e.g., 2.0 means 1:2 risk-reward)
            
        Example:
            - price = 50000
            - tp = 52000 (reward = 2000)
            - sl = 49000 (risk = 1000)
            -> R:R = 2000/1000 = 2.0 (1:2 ratio)
        """
        risk = abs(price - sl)
        reward = abs(tp - price)
        
        if risk == 0:
            return 0
            
        return reward / risk

    async def compute_leveraged_volume(self, *, balance: float, price: float, leverage: float = 1.0,
                                      risk_percent: float = 100.0, round_down: bool = False) -> float:
        """
        Compute volume with leverage for crypto futures trading.
        
        Args:
            balance (float): Account balance
            price (float): Entry price
            leverage (float): Leverage multiplier (e.g., 10.0 for 10x)
            risk_percent (float): Percentage of balance to use (default 100%)
            round_down (bool): Round down volume
            
        Returns:
            float: Volume that can be traded with leverage
            
        Example:
            - balance = 1000 USDT
            - price = 50000 USDT
            - leverage = 10x
            - risk_percent = 50% (use 500 USDT)
            -> buying_power = 500 * 10 = 5000 USDT
            -> volume = 5000 / 50000 = 0.1 BTC
        """
        capital_to_use = balance * (risk_percent / 100)
        buying_power = capital_to_use * leverage
        
        if price == 0:
            return self.volume_min
            
        volume = buying_power / (price * self.trade_contract_size)
        return self.round_off_volume(volume=volume, round_down=round_down)

    def get_min_notional(self, *, price: float, min_notional_value: float = 10.0) -> float:
        """
        Calculate minimum volume required to meet exchange's minimum notional value.
        Most crypto exchanges have minimum order value requirements.
        
        Args:
            price (float): Current price
            min_notional_value (float): Minimum order value required (e.g., 10 USDT)
            
        Returns:
            float: Minimum volume required
            
        Example:
            Binance requires min 10 USDT order:
            - BTCUSDT price = 50000
            -> min_volume = 10 / 50000 = 0.0002 BTC
        """
        if price == 0:
            return self.volume_min
            
        min_volume = min_notional_value / (price * self.trade_contract_size)
        return max(min_volume, self.volume_min)