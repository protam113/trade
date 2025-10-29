from logging import getLogger

from ..core.models import TradeRequest, TradeOrder, OrderCheckResult, OrderSendResult
from ..core.constants import TradeAction, OrderTime, OrderFilling, OrderType
from ..core.exceptions import OrderError
from ..core.base import _Base
from ..utils import error_handler, percentage_decrease, percentage_increase

logger = getLogger(__name__)


class Order(_Base, TradeRequest):
    """Trade order related functions and properties. Subclass of TradeRequest."""
    def __init__(self, **kwargs):
        """
        Initialize the order object with keyword arguments.
        Auto-detect the correct filling mode for the symbol to avoid 'Unsupported filling mode' errors.
        """
        from MetaTrader5 import symbol_info, ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN

        symbol_name = kwargs.get("symbol")
        default_filling = ORDER_FILLING_RETURN  # fallback mặc định

        # 🔍 Auto detect filling mode từ MT5
        if symbol_name:
            info = symbol_info(symbol_name)
            if info and hasattr(info, "filling_mode"):
                filling_mode = info.filling_mode
                print(f">>> Symbol {symbol_name} supports filling_mode: {filling_mode}")
                
                # Chọn filling mode theo thứ tự ưu tiên: FOK > IOC > RETURN
                if filling_mode & 1:  # Bit 0: FOK
                    default_filling = ORDER_FILLING_FOK
                    print(f"    ✅ Using ORDER_FILLING_FOK")
                elif filling_mode & 2:  # Bit 1: IOC
                    default_filling = ORDER_FILLING_IOC
                    print(f"    ✅ Using ORDER_FILLING_IOC")
                else:  # Bit 2: RETURN
                    default_filling = ORDER_FILLING_RETURN
                    print(f"    ✅ Using ORDER_FILLING_RETURN")

        # ⚙️ Gán cấu hình mặc định
        kwargs.setdefault("action", TradeAction.DEAL)
        kwargs.setdefault("type_time", OrderTime.DAY)
        kwargs.setdefault("type_filling", default_filling)

        super().__init__(**kwargs)



    def modify(self, **kwargs):
        """Modify the order object with keyword arguments.

        Args:
            **kwargs: Keyword arguments must match the attributes of TradeRequest as well as the attributes of
             Order class as specified in the annotations in the class definition.
        """
        self.set_attributes(**kwargs)

    @classmethod
    async def orders_total(cls):
        """Get the number of active pending orders.

        Returns:
            (int): total number of active pending orders
        """
        return await cls.mt5.orders_total()

    @classmethod
    async def get_pending_order(cls, *, ticket: int) -> TradeOrder | None:
        """
        Get a pending order by ticket number.

        Args:
            ticket (int): Order ticket number

        Returns:
        """
        orders = await cls.mt5.orders_get(ticket=ticket)
        order = None
        for order_ in orders:
            if order_.ticket == ticket:
                return TradeOrder(**order_._asdict())
        return order

    @classmethod
    async def get_pending_orders(cls, *, ticket: int = 0, symbol: str = "", group: str = "") -> tuple[TradeOrder, ...]:
        """Get the list of active pending orders for the current symbol.

        Args:
            ticket (int): Order ticket number
            symbol (str): Symbol name
            group (str): Group name

        Returns:
            tuple[TradeOrder, ...]: A Tuple of active pending trade orders as TradeOrder objects
        """
        orders = await cls.mt5.orders_get(symbol=symbol, ticket=ticket, group=group)
        if orders is not None:
            return tuple(TradeOrder(**order._asdict()) for order in orders)
        return tuple()

    @classmethod
    async def cancel_order(cls, *, order: int, symbol: str) -> OrderSendResult:
        """Cancel an active pending order by ticket number."""
        res = await cls.mt5.order_send({"symbol": symbol, "order": order, "action": TradeAction.REMOVE})
        return res

    async def check(self, **kwargs) -> OrderCheckResult:
        """Check funds sufficiency for performing a required trading operation and the possibility of executing it.

        Returns:
            OrderCheckResult: An OrderCheckResult object

        Raises:
            OrderError: If not successful
        """
        req = self.request | kwargs
        res = await self.mt5.order_check(req)
        if res is None:
            raise OrderError(f"Order check failed for {self.symbol}")
        return OrderCheckResult(**res._asdict())

    async def send(self) -> OrderSendResult:
        """Send a request to perform a trading operation from the terminal to the trade server.

        Returns:
             OrderSendResult: An OrderSendResult object

        Raises:
            OrderError: If not successful
        """
        res = await self.mt5.order_send(self.request)
        if res is None:
            raise OrderError(f"Failed to send order {self.symbol}")
        return OrderSendResult(**res._asdict())

    @error_handler(log_error_msg=False)
    async def calc_margin(self) -> float | None:
        """Return the required margin in the account currency to perform a specified trading operation.

        Returns:
            float: Returns float value if successful
        """
        res = await self.mt5.order_calc_margin(self.type, self.symbol, self.volume, self.price)
        return res

    @error_handler(log_error_msg=False)
    async def calc_profit(self) -> float:
        """Return profit in the account currency for a specified trading operation.

        Returns:
            float: Returns float value if successful
            None: If not successful
        """
        action, symbol, volume, price_open, price_close = (self.type, self.symbol, self.volume, self.price, self.tp)
        res = await self.mt5.order_calc_profit(action, symbol, volume, price_open, price_close)
        return res

    @error_handler(log_error_msg=False)
    async def calc_loss(self) -> float:
        """Return profit in the account currency for a specified trading operation.

        Returns:
            float: Returns float value if successful
            None: If not successful
        """
        action, symbol, volume, price_open, price_close = (self.type, self.symbol, self.volume, self.price, self.sl)
        res = await self.mt5.order_calc_profit(action, symbol, volume, price_open, price_close)
        return res

    @property
    def request(self) -> dict:
        """Return the order request as a dictionary, ensuring type_filling is always included."""
        req = self.dict.copy()

        # 🔧 Đảm bảo có type_filling trong request
        if "type_filling" not in req or req["type_filling"] is None:
            from MetaTrader5 import ORDER_FILLING_RETURN
            req["type_filling"] = ORDER_FILLING_RETURN

        # Không lọc bằng __match_args__ nữa — tránh mất field quan trọng
        return req


    @classmethod
    async def profit_to_price(cls, *, profit: float, order_type: OrderType, volume: float, symbol: str, price_open: float):
        price_close = percentage_increase(price_open, 50) if order_type == 0 else percentage_decrease(price_open, 50)
        half_profit = await cls.mt5.order_calc_profit(symbol=symbol, action=order_type, volume=volume,
                                             price_open=price_open, price_close=price_close)
        rate = profit / half_profit * 50
        rate = percentage_increase(price_open, rate) if order_type == 0 else percentage_decrease(price_open, rate)
        return rate
