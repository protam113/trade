# MACD Trading Bot

Bot trading sử dụng chỉ báo MACD (Moving Average Convergence Divergence) để phân tích và giao dịch.

## Tổng quan

Bot này sử dụng MACD để:
- Phát hiện xu hướng (trend)
- Xác định điểm vào lệnh (entry points)
- Phân tích động lượng (momentum)

## Cấu trúc thư mục

```
bot_macd/
├── macd_indicator.py    # Module tính toán MACD
├── macd_bot.py          # Bot trading chính
├── config_macd.py       # Cấu hình bot
└── README_MACD.md       # File hướng dẫn này
```

## Cài đặt

1. Đảm bảo đã cài đặt các dependencies từ `requirements.txt` ở thư mục gốc:
```bash
pip install -r requirements.txt
```

2. Cấu hình thông tin kết nối trong file `.env` (ở thư mục gốc):
```
MT5_ACCOUNT=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=Exness-Demo
```

## Cấu hình MACD

Trong file `config_macd.py`, bạn có thể điều chỉnh:

### Tham số MACD chuẩn:
- `MACD_FAST = 12` - Fast EMA period
- `MACD_SLOW = 26` - Slow EMA period
- `MACD_SIGNAL = 9` - Signal line EMA period

### Tham số MACD tối ưu cho M5 Scalping:
Để dùng cho scalping trên timeframe M5, uncomment trong `config_macd.py`:
```python
MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 5
```

## Chiến lược MACD

Bot sử dụng các tín hiệu MACD sau:

### Tín hiệu BUY:
1. **MACD line vượt lên Signal line** (Bullish crossover) - Điểm: +3
2. **Histogram > 0 và đang tăng** (Động lượng bullish mạnh) - Điểm: +2
3. **MACD line > 0** (Bullish trend) - Điểm: +1

**Tổng điểm tối thiểu để vào lệnh BUY: 4 điểm**

### Tín hiệu SELL:
1. **MACD line vượt xuống Signal line** (Bearish crossover) - Điểm: +3
2. **Histogram < 0 và đang giảm** (Động lượng bearish mạnh) - Điểm: +2
3. **MACD line < 0** (Bearish trend) - Điểm: +1

**Tổng điểm tối thiểu để vào lệnh SELL: 4 điểm**

### Multi-Timeframe Analysis

Bot phân tích trên nhiều timeframe và kết hợp tín hiệu với trọng số:
- **1h**: 35% - Xác định xu hướng chính
- **15m**: 30% - Xu hướng trung hạn
- **5m**: 20% - Tìm điểm vào
- **1m**: 15% - Vào lệnh chính xác

## Chạy Bot

Từ thư mục gốc của project:
```bash
python bot_macd/macd_bot.py
```

Hoặc từ thư mục `bot_macd`:
```bash
cd bot_macd
python macd_bot.py
```

## Logging

Bot sẽ ghi log vào file `bot_macd/macd_bot.log` và hiển thị trên console.

## Lưu ý

1. **Bot này hoàn toàn độc lập** với bot Ichimoku+Bollinger Bands ở thư mục gốc
2. Cả hai bot có thể chạy đồng thời nếu cần
3. Bot sử dụng chung `exness_connector.py` từ thư mục gốc
4. Cấu hình riêng biệt trong `config_macd.py`

## Cấu hình Risk Management

Trong `config_macd.py`:
- `STOP_LOSS_PIPS = 20.0` - Stop loss 20 pip
- `TAKE_PROFIT_PIPS = 40.0` - Take profit 40 pip
- `LOT_SIZE = 0.1` - Kích thước lot mặc định
- `MIN_CONFIDENCE = 0.5` - Độ tin cậy tối thiểu để vào lệnh

## Tùy chỉnh

### Thay đổi symbols:
Sửa trong `config_macd.py`:
```python
SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", ...]
```

### Thay đổi timeframes:
Sửa trong `config_macd.py`:
```python
TIMEFRAMES = ["1h", "15m", "5m", "1m"]
```

### Thay đổi trọng số timeframe:
Sửa trong `config_macd.py`:
```python
TIMEFRAME_WEIGHTS = {
    "1h": 35,
    "15m": 30,
    "5m": 20,
    "1m": 15
}
```

## Troubleshooting

### Lỗi import:
Nếu gặp lỗi import `exness_connector`, đảm bảo bạn chạy bot từ thư mục gốc hoặc đã cấu hình đúng path.

### Lỗi kết nối MT5:
- Kiểm tra MetaTrader 5 đã được cài đặt
- Kiểm tra thông tin đăng nhập trong `.env`
- Kiểm tra server name (Exness-Demo hoặc Exness-Real)

### MACD không tính được:
- Đảm bảo có đủ dữ liệu (ít nhất `MACD_SLOW + MACD_SIGNAL` nến)
- Nếu dùng TA-Lib, kiểm tra đã cài đặt: `pip install TA-Lib`

