import enum

class TradeMode(enum.Enum):
    """
    Enum representing the available trading modes.
    """
    NORMAL = "normal"       # Allow both buy and sell
    BUY_ONLY = "buy_only"   # Only allow buy trades
    SELL_ONLY = "sell_only" # Only allow sell trades


class TradeModeController:
    """
    Controller to manage and check the current trading mode.
    """

    def __init__(self, mode: TradeMode = TradeMode.NORMAL):
        """
        Initialize the controller with a given trading mode.

        Parameters
        ----------
        mode : TradeMode, optional
            The initial trading mode (default is NORMAL).
        """
        self.mode = mode

    def set_mode(self, new_mode: TradeMode):
        """
        Update the trading mode.

        Parameters
        ----------
        new_mode : TradeMode
            The new trading mode to be set.
        """
        self.mode = new_mode
        self.print_mode_status()

    def is_trade_allowed(self, direction: str) -> bool:
        """
        Check if a trade is allowed under the current mode.

        Parameters
        ----------
        direction : str
            Trade direction ('buy' or 'sell').

        Returns
        -------
        bool
            True if allowed, False otherwise.
        """
        direction = direction.lower()

        if self.mode == TradeMode.NORMAL:
            return True
        if self.mode == TradeMode.BUY_ONLY and direction == "buy":
            return True
        if self.mode == TradeMode.SELL_ONLY and direction == "sell":
            return True

        return False

    def print_mode_status(self):
        """
        Print the current trading mode status.
        """
        if self.mode == TradeMode.NORMAL:
            print("Mode: NORMAL — allows both BUY & SELL ✅")
        elif self.mode == TradeMode.BUY_ONLY:
            print("Mode: BUY ONLY — only long trades allowed 🟢")
        elif self.mode == TradeMode.SELL_ONLY:
            print("Mode: SELL ONLY — only short trades allowed 🔴")