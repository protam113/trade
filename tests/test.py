from src.v1.contrib.strategies.dca import DCAGroup

# Giả sử đang trade buy
dca = DCAGroup(side="buy")

# Thêm 3 cấp DCA
dca.add_order(entry=1.0850, volume=0.1, stoploss=1.0820)
dca.add_order(entry=1.0865, volume=0.1, stoploss=1.0835)
dca.add_order(entry=1.0875, volume=0.1, stoploss=1.0845)

# Cập nhật giá hiện tại
dca.update_current_price(1.0890)

print("✅ All profitable:", dca.all_profitable())
print("📊 Average entry:", dca.get_average_entry())
print("🧱 Deepest stoploss:", dca.get_max_stoploss())
