# trailing.py
import pandas as pd

class TrailingStop:
    """
    Manage trailing stop logic based on DCA positions.
    """

    def __init__(self, trail_pips: float = 35):
        """
        Initialize the trailing stop controller.

        Parameters
        ----------
        trail_pips : float, optional
            The distance (in pips) to keep between price and stop loss. Default is 35 pips.
        """
        self.trail_pips = trail_pips
        self.activated = False

    def should_activate(self, dca_positions: list[dict]) -> bool:
        """
        Check if trailing stop should be activated.

        Parameters
        ----------
        dca_positions : list of dict
            Each dict represents a DCA level with keys like:
            {
                'entry': float,   # Entry price
                'current': float, # Current price
                'side': 'buy' or 'sell'
            }

        Returns
        -------
        bool
            True if all DCA levels are in profit, False otherwise.
        """
        if not dca_positions:
            return False

        all_profitable = True
        for pos in dca_positions:
            entry = pos["entry"]
            current = pos["current"]
            side = pos["side"]

            if side == "buy" and current <= entry:
                all_profitable = False
                break
            if side == "sell" and current >= entry:
                all_profitable = False
                break

        self.activated = all_profitable
        return all_profitable

    def get_new_stoploss(self, current_price: float, side: str) -> float | None:
        """
        Calculate new stop loss when trailing is active.

        Parameters
        ----------
        current_price : float
            Current market price.
        side : str
            'buy' or 'sell'

        Returns
        -------
        float or None
            New stop loss level if trailing is active, else None.
        """
        if not self.activated:
            return None

        pip_value = self.trail_pips * 0.0001

        if side == "buy":
            return current_price - pip_value
        elif side == "sell":
            return current_price + pip_value
        return None

    def __repr__(self):
        return f"<TrailingStop active={self.activated} trail={self.trail_pips}pips>"
