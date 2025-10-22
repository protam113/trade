from dataclasses import dataclass, field
from typing import List, Literal


@dataclass
class DCAOrder:
    """Đại diện cho một cấp DCA."""
    entry: float
    volume: float
    stoploss: float
    side: Literal["buy", "sell"]
    current: float = 0.0

    def profit_pips(self) -> float:
        """Tính lãi/lỗ của lệnh hiện tại theo pip."""
        diff = (self.current - self.entry) * 10000
        return diff if self.side == "buy" else -diff

    def is_profitable(self) -> bool:
        """Kiểm tra lệnh có đang lãi hay không."""
        return self.profit_pips() > 0


@dataclass
class DCAGroup:
    """Quản lý toàn bộ các cấp DCA."""
    side: Literal["buy", "sell"]
    orders: List[DCAOrder] = field(default_factory=list)

    def add_order(self, entry: float, volume: float, stoploss: float):
        """Thêm một cấp DCA mới."""
        self.orders.append(DCAOrder(entry=entry, volume=volume, stoploss=stoploss, side=self.side))

    def update_current_price(self, price: float):
        """Cập nhật giá hiện tại cho toàn bộ lệnh."""
        for o in self.orders:
            o.current = price

    def all_profitable(self) -> bool:
        """Kiểm tra xem tất cả các cấp DCA có đang có lãi hay không."""
        return all(o.is_profitable() for o in self.orders)

    def get_average_entry(self) -> float:
        """Tính giá trung bình của tất cả cấp DCA."""
        if not self.orders:
            return 0.0
        total_value = sum(o.entry * o.volume for o in self.orders)
        total_volume = sum(o.volume for o in self.orders)
        return total_value / total_volume

    def get_max_stoploss(self) -> float:
        """Lấy stoploss sâu nhất (xấu nhất) trong tất cả lệnh."""
        if not self.orders:
            return 0.0
        if self.side == "buy":
            return min(o.stoploss for o in self.orders)
        return max(o.stoploss for o in self.orders)
