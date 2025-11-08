from logging import getLogger

from ...core.models import OrderType
from ...lib.trader import Trader

logger = getLogger(__name__)


class ScalpTrader(Trader):
    """Scalp Trader với khả năng đặt lệnh có hoặc không có TP/SL"""
    
    async def place_trade(self, *, order_type: OrderType, volume: float = None, parameters: dict = None):
        """Places a trade without stop_loss or take_profit.
        
        Args:
            order_type (OrderType): The order_type
            volume (float): The volume to trade
            parameters (dict): Parameters associated with the trade
        """
        try:
            self.parameters |= parameters or {}
            volume = volume or self.symbol.volume_min
            await self.create_order_no_stops(order_type=order_type, volume=volume)
            if not await self.check_order():
                return
            self.order.comment = self.parameters.get("name", self.__class__.__name__)
            res = await self.send_order()
            if res is not None:
                await self.record_trade(result=res, parameters=self.parameters)
        except Exception as err:
            logger.error(f"{err} in {self.__class__.__name__}.place_trade for {self.symbol.name}")
    
    async def place_trade_with_sl_tp(
        self, 
        *, 
        order_type: OrderType, 
        volume: float = None, 
        sl: float = None,
        tp: float = None,
        parameters: dict = None
    ):
        """Places a trade WITH stop_loss and take_profit.
        
        Args:
            order_type (OrderType): BUY or SELL
            volume (float): Lot size (default: symbol minimum)
            sl (float): Stop Loss price
            tp (float): Take Profit price
            parameters (dict): Additional parameters
        
        Returns:
            bool: True if trade successful, False otherwise
        """
        try:
            self.parameters |= parameters or {}
            volume = volume or self.symbol.volume_min
            
            # Create order with SL/TP
            if self.parameters.get("use_fixed_lot", False):
                await self.create_order_fixed_lot(
                    order_type=order_type,
                    volume=self.parameters.get("lot_size", 0.01),
                    sl=sl,
                    tp=tp
                )
            else:
                await self.create_order_with_stops(
                    order_type=order_type,
                    sl=sl,
                    tp=tp
                )

            
            if not await self.check_order():
                logger.warning(f"⚠️ {self.symbol.name} Order check failed")
                return False
            
            # Set comment
            self.order.comment = self.parameters.get("name", self.__class__.__name__)
            
            # Send order
            res = await self.send_order()
            
            if res is not None:
                await self.record_trade(result=res, parameters=self.parameters)
                logger.info(f"✅ {self.symbol.name} Trade recorded: {order_type}")
                return True
            else:
                logger.error(f"❌ {self.symbol.name} Send order returned None")
                return False
                
        except Exception as err:
            logger.error(f"❌ {self.__class__.__name__}.place_trade_with_sl_tp failed for {self.symbol.name}: {err}", exc_info=True)
            return False