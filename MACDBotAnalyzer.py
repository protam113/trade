# audusd , euraud  ,eurcad, eurnzd , gbpaud,gbpnzd, gbpusd , nzdchf* , nzdjpy , nzdusd, usdcad ,usdjpy,

import pandas as pd
import numpy as np
from datetime import datetime
import json

def analyze_macd_bot(csv_file='my_trades.csv'):
    """Phân tích chi tiết performance của MACD bot"""
    
    # Đọc dữ liệu
    df = pd.read_csv(csv_file)
    
    print("="*80)
    print("📊 MACD BOT PERFORMANCE ANALYSIS")
    print("="*80)
    print(f"Total records loaded: {len(df)}")
    
    # ========== LỌC TRADES HỢP LỆ ==========
    # Chỉ lấy CLOSED trades (entry=1 hoặc reason != 3)
    # reason=3 là OPEN position, reason=0,1,4,5 là CLOSE
    closed_trades = df[df['entry'] == 1].copy()
    
    # Loại bỏ trades không có comment hoặc không phải MACD strategies
    closed_trades = closed_trades[
        closed_trades['comment'].notna() & 
        (closed_trades['comment'].str.contains('MACD|EMA|Scalp', case=False, na=False))
    ]
    
    print(f"Closed trades with MACD strategies: {len(closed_trades)}")
    
    if len(closed_trades) == 0:
        print("\n⚠️  Không tìm thấy closed trades hợp lệ!")
        return None
    
    # ========== METRICS TỔNG THỂ ==========
    total_trades = len(closed_trades)
    winning_trades = closed_trades[closed_trades['profit'] > 0]
    losing_trades = closed_trades[closed_trades['profit'] < 0]
    breakeven_trades = closed_trades[closed_trades['profit'] == 0]
    
    total_profit = closed_trades['profit'].sum()
    total_win = winning_trades['profit'].sum()
    total_loss = abs(losing_trades['profit'].sum())
    
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
    profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
    
    avg_win = winning_trades['profit'].mean() if len(winning_trades) > 0 else 0
    avg_loss = abs(losing_trades['profit'].mean()) if len(losing_trades) > 0 else 0
    expectancy = (win_rate/100 * avg_win) - ((100-win_rate)/100 * avg_loss)
    
    # Max Drawdown
    closed_trades = closed_trades.sort_values('time')
    closed_trades['cumulative_profit'] = closed_trades['profit'].cumsum()
    closed_trades['running_max'] = closed_trades['cumulative_profit'].cummax()
    closed_trades['drawdown'] = closed_trades['running_max'] - closed_trades['cumulative_profit']
    max_drawdown = closed_trades['drawdown'].max()
    
    # Time analysis
    closed_trades['time'] = pd.to_datetime(closed_trades['time'])
    first_trade = closed_trades['time'].min()
    last_trade = closed_trades['time'].max()
    trading_hours = (last_trade - first_trade).total_seconds() / 3600
    trading_days = (last_trade - first_trade).days + 1
    
    print(f"\n📈 TỔNG QUAN")
    print(f"   Tổng closed trades: {total_trades}")
    print(f"   Thời gian: {first_trade.strftime('%Y-%m-%d %H:%M')} → {last_trade.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Duration: {trading_days} ngày ({trading_hours:.1f} giờ)")
    print(f"   Trades/giờ: {total_trades/trading_hours:.1f}")
    print(f"   Trades/ngày: {total_trades/trading_days:.1f}")
    
    print(f"\n💰 PROFIT & LOSS")
    print(f"   Total P/L: ${total_profit:.2f}")
    print(f"   Win: {len(winning_trades)} | Loss: {len(losing_trades)} | BE: {len(breakeven_trades)}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    print(f"   Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")
    print(f"   Expectancy: ${expectancy:.3f} per trade")
    print(f"   Max Drawdown: ${max_drawdown:.2f}")
    
    # R:R Ratio thực tế
    rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    print(f"   Actual R:R Ratio: {rr_ratio:.2f}:1")
    
    # ========== PHÂN TÍCH THEO STRATEGY ==========
    print(f"\n📊 PERFORMANCE THEO STRATEGY")
    print("-"*80)
    
    for strategy in sorted(closed_trades['comment'].unique()):
        strategy_df = closed_trades[closed_trades['comment'] == strategy]
        wins = len(strategy_df[strategy_df['profit'] > 0])
        losses = len(strategy_df[strategy_df['profit'] < 0])
        total = len(strategy_df)
        profit = strategy_df['profit'].sum()
        win_rate_strat = (wins / total * 100) if total > 0 else 0
        
        avg_profit = profit / total
        
        print(f"\n   📌 {strategy}")
        print(f"      Trades: {total} ({wins}W/{losses}L)")
        print(f"      P/L: ${profit:.2f}")
        print(f"      Win Rate: {win_rate_strat:.1f}%")
        print(f"      Avg P/L: ${avg_profit:.3f}")
    
    # ========== PHÂN TÍCH THEO SYMBOL ==========
    print(f"\n📊 PERFORMANCE THEO SYMBOL")
    print("-"*80)
    
    symbol_stats = closed_trades.groupby('symbol').agg({
        'profit': ['count', 'sum', 'mean']
    }).round(3)
    symbol_stats.columns = ['Trades', 'Total_PL', 'Avg_PL']
    symbol_stats = symbol_stats.sort_values('Total_PL', ascending=False)
    
    # Calculate win rate per symbol
    symbol_wr = {}
    for symbol in closed_trades['symbol'].unique():
        symbol_df = closed_trades[closed_trades['symbol'] == symbol]
        wins = len(symbol_df[symbol_df['profit'] > 0])
        symbol_wr[symbol] = (wins / len(symbol_df) * 100) if len(symbol_df) > 0 else 0
    
    print("\n🏆 TOP 10 SYMBOLS:")
    for idx, row in symbol_stats.head(10).iterrows():
        wr = symbol_wr.get(idx, 0)
        print(f"   {idx:8s} | {int(row['Trades']):3d} trades | ${row['Total_PL']:7.2f} | WR: {wr:5.1f}% | Avg: ${row['Avg_PL']:.3f}")
    
    print("\n💀 WORST 10 SYMBOLS:")
    for idx, row in symbol_stats.tail(10).iterrows():
        wr = symbol_wr.get(idx, 0)
        print(f"   {idx:8s} | {int(row['Trades']):3d} trades | ${row['Total_PL']:7.2f} | WR: {wr:5.1f}% | Avg: ${row['Avg_PL']:.3f}")
    
    # ========== PHÂN TÍCH THEO DIRECTION ==========
    print(f"\n📊 PERFORMANCE THEO HƯỚNG")
    print("-"*80)
    
    # Tìm direction từ OPEN position (entry=0)
    open_positions = df[df['entry'] == 0].copy()
    direction_map = dict(zip(open_positions['position_id'], open_positions['type']))
    closed_trades['direction'] = closed_trades['position_id'].map(direction_map)
    
    buy_df = closed_trades[closed_trades['direction'] == 0]
    sell_df = closed_trades[closed_trades['direction'] == 1]
    
    buy_win_rate = (len(buy_df[buy_df['profit'] > 0]) / len(buy_df) * 100) if len(buy_df) > 0 else 0
    sell_win_rate = (len(sell_df[sell_df['profit'] > 0]) / len(sell_df) * 100) if len(sell_df) > 0 else 0
    
    print(f"\n   📈 BUY Trades:")
    print(f"      Count: {len(buy_df)}")
    print(f"      P/L: ${buy_df['profit'].sum():.2f}")
    print(f"      Win Rate: {buy_win_rate:.1f}%")
    print(f"      Avg: ${buy_df['profit'].mean():.3f}")
    
    print(f"\n   📉 SELL Trades:")
    print(f"      Count: {len(sell_df)}")
    print(f"      P/L: ${sell_df['profit'].sum():.2f}")
    print(f"      Win Rate: {sell_win_rate:.1f}%")
    print(f"      Avg: ${sell_df['profit'].mean():.3f}")
    
    # ========== PHÂN TÍCH EXIT TYPE ==========
    print(f"\n📊 PHÂN TÍCH EXIT TYPE")
    print("-"*80)
    
    # Phân loại exit type dựa vào comment
    closed_trades['exit_type'] = 'Manual'
    closed_trades.loc[closed_trades['comment'].str.contains(r'\[sl', case=False, na=False), 'exit_type'] = 'Stop Loss'
    closed_trades.loc[closed_trades['comment'].str.contains(r'\[tp', case=False, na=False), 'exit_type'] = 'Take Profit'
    
    for exit_type in ['Stop Loss', 'Take Profit', 'Manual']:
        exit_df = closed_trades[closed_trades['exit_type'] == exit_type]
        if len(exit_df) > 0:
            count = len(exit_df)
            pct = (count / total_trades * 100)
            total_pl = exit_df['profit'].sum()
            avg_pl = exit_df['profit'].mean()
            
            print(f"\n   {exit_type}: {count} ({pct:.1f}%)")
            print(f"      Total P/L: ${total_pl:.2f}")
            print(f"      Avg P/L: ${avg_pl:.3f}")
    
    # ========== PHÂN TÍCH REASON CODE ==========
    print(f"\n📊 PHÂN TÍCH REASON CODE")
    print("-"*80)
    reason_map = {
        0: "Expert (EA close)",
        1: "Manual close",
        2: "Mobile close", 
        3: "Position open",
        4: "Stop Loss hit",
        5: "Take Profit hit"
    }
    
    reason_counts = closed_trades['reason'].value_counts()
    for reason, count in reason_counts.items():
        reason_df = closed_trades[closed_trades['reason'] == reason]
        pct = (count / total_trades * 100)
        pl = reason_df['profit'].sum()
        print(f"   Reason {reason} ({reason_map.get(reason, 'Unknown')}): {count} ({pct:.1f}%) | P/L: ${pl:.2f}")
    
    # ========== VẤN ĐỀ & ĐỀ XUẤT ==========
    print(f"\n{'='*80}")
    print("⚠️  VẤN ĐỀ PHÁT HIỆN & ĐỀ XUẤT")
    print("="*80)
    
    issues = []
    
    # 1. Win rate
    if win_rate < 40:
        issues.append({
            'severity': '🔴 CRITICAL',
            'title': f'Win Rate RẤT THẤP: {win_rate:.1f}%',
            'solution': [
                '→ Tăng ADX threshold từ 30 → 40 (filter mạnh hơn)',
                '→ Tăng vol_multiplier từ 2.5 → 3.5',
                '→ Thêm minimum MACD histogram threshold',
                '→ Xem xét chỉ trade khi HTF trend rõ ràng (score 3/3)'
            ]
        })
    elif win_rate < 50:
        issues.append({
            'severity': '🟡 WARNING',
            'title': f'Win Rate thấp: {win_rate:.1f}%',
            'solution': [
                '→ Tăng ADX threshold từ 30 → 35',
                '→ Tăng vol_multiplier từ 2.5 → 3.0',
                '→ Review lại HTF trend filter'
            ]
        })
    
    # 2. Profit factor
    if profit_factor < 1.0:
        issues.append({
            'severity': '🔴 CRITICAL',
            'title': f'Profit Factor < 1.0: {profit_factor:.2f} (ĐANG THUA LỖ)',
            'solution': [
                '→ DỪNG BOT NGAY và review lại toàn bộ strategy',
                '→ Backtest lại trên data lịch sử',
                '→ Xem xét thay đổi cơ bản logic'
            ]
        })
    elif profit_factor < 1.2:
        issues.append({
            'severity': '🟡 WARNING',
            'title': f'Profit Factor thấp: {profit_factor:.2f}',
            'solution': [
                '→ Tăng TP/SL ratio: tp_factor từ 2.0 → 3.0',
                '→ Giảm sl_factor từ 1.0 → 0.8',
                '→ Cân nhắc trailing stop'
            ]
        })
    
    # 3. Expectancy
    if expectancy < 0:
        issues.append({
            'severity': '🔴 CRITICAL',
            'title': f'Expectancy âm: ${expectancy:.3f} (Mỗi trade bị lỗ trung bình)',
            'solution': [
                '→ Strategy không profitable, cần overhaul toàn bộ',
                '→ Review lại entry conditions',
                '→ Kiểm tra spread/commission có ảnh hưởng không'
            ]
        })
    
    # 4. SL hit rate
    sl_trades = closed_trades[closed_trades['exit_type'] == 'Stop Loss']
    sl_rate = (len(sl_trades) / total_trades * 100) if total_trades > 0 else 0
    
    if sl_rate > 70:
        issues.append({
            'severity': '🟡 WARNING',
            'title': f'SL hit quá nhiều: {sl_rate:.1f}%',
            'solution': [
                '→ SL quá gần hoặc entry không tốt',
                '→ Tăng sl_factor từ 1.0 → 1.2-1.5',
                '→ Hoặc filter entry kỹ hơn'
            ]
        })
    
    # 5. TP hit rate
    tp_trades = closed_trades[closed_trades['exit_type'] == 'Take Profit']
    tp_rate = (len(tp_trades) / total_trades * 100) if total_trades > 0 else 0
    
    if tp_rate < 20:
        issues.append({
            'severity': '🟡 WARNING',
            'title': f'TP hit quá ít: {tp_rate:.1f}%',
            'solution': [
                '→ TP quá xa, giảm tp_factor từ 2.0 → 1.5',
                '→ Hoặc thêm trailing stop để bảo vệ profit'
            ]
        })
    
    # 6. Overtrading
    trades_per_day = total_trades / trading_days
    if trades_per_day > 100:
        issues.append({
            'severity': '🔴 CRITICAL',
            'title': f'OVERTRADING NGHIÊM TRỌNG: {trades_per_day:.1f} trades/ngày',
            'solution': [
                '→ Tăng interval_seconds từ 120 → 300-600',
                '→ Thêm min_signal_gap_minutes: 15-30',
                '→ Giảm max_open_signals từ 15 → 5-8',
                '→ Spread/commission đang ăn mất lợi nhuận'
            ]
        })
    elif trades_per_day > 50:
        issues.append({
            'severity': '🟡 WARNING',
            'title': f'Overtrading: {trades_per_day:.1f} trades/ngày',
            'solution': [
                '→ Tăng interval_seconds từ 120 → 180-240',
                '→ Thêm min_signal_gap_minutes: 10-15'
            ]
        })
    
    # 7. Strategy specific issues
    strategy_performance = closed_trades.groupby('comment')['profit'].sum().sort_values()
    worst_strategy_profit = strategy_performance.iloc[0]
    worst_strategy_name = strategy_performance.index[0]
    
    if worst_strategy_profit < -5:
        issues.append({
            'severity': '🟡 WARNING',
            'title': f'Strategy "{worst_strategy_name}" thua lỗ: ${worst_strategy_profit:.2f}',
            'solution': [
                f'→ TẮT strategy này trong config',
                f'→ Hoặc review lại logic'
            ]
        })
    
    # 8. Symbol specific issues
    losing_symbols = symbol_stats[symbol_stats['Total_PL'] < -2]
    if len(losing_symbols) > 5:
        top_losers = losing_symbols.head(5).index.tolist()
        issues.append({
            'severity': '🟡 WARNING',
            'title': f'{len(losing_symbols)} symbols thua lỗ > $2',
            'solution': [
                f'→ Blacklist: {", ".join(top_losers)}',
                f'→ Hoặc tăng filter riêng cho các symbols này'
            ]
        })
    
    # 9. Direction bias
    if len(buy_df) > 0 and len(sell_df) > 0:
        if abs(buy_win_rate - sell_win_rate) > 20:
            better_dir = "BUY" if buy_win_rate > sell_win_rate else "SELL"
            worse_dir = "SELL" if better_dir == "BUY" else "BUY"
            issues.append({
                'severity': '🔵 INFO',
                'title': f'Direction bias mạnh: {better_dir} {max(buy_win_rate, sell_win_rate):.1f}% vs {worse_dir} {min(buy_win_rate, sell_win_rate):.1f}%',
                'solution': [
                    f'→ Xem xét chỉ trade {better_dir} trong trending market',
                    f'→ Hoặc tăng filter cho {worse_dir} trades'
                ]
            })
    
    # 10. R:R ratio check
    if rr_ratio < 1.0:
        issues.append({
            'severity': '🔴 CRITICAL',
            'title': f'R:R Ratio thực tế quá thấp: {rr_ratio:.2f}:1',
            'solution': [
                '→ Avg Win < Avg Loss → Không bền vững',
                '→ Tăng TP hoặc giảm SL',
                '→ Hoặc cải thiện entry để win lớn hơn'
            ]
        })
    
    # Print issues
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue['severity']} {issue['title']}")
            for sol in issue['solution']:
                print(f"   {sol}")
    else:
        print("\n✅ Bot đang chạy TỐT! Không có vấn đề nghiêm trọng phát hiện.")
    
    # ========== CONFIG TỐI ƯU ==========
    print(f"\n{'='*80}")
    print("⚙️  CONFIG TỐI ƯU ĐỀ XUẤT")
    print("="*80)
    
    # Base config
    optimized_config = {
        "strategy": {
            "macd": {
                "fast": 12,
                "slow": 26,
                "signal": 9
            },
            "risk_management": {
                "tp_pips": 20,
                "sl_pips": 10,
                "lot_size": 0.01
            },
            "volatility_filter": {
                "enabled": True,
                "atr_length": 14,
                "multiplier": 2.5,
                "tp_factor": 2.0,
                "sl_factor": 1.0,
                "adx_threshold": 30
            },
            "execution": {
                "max_open_signals": 15,
                "interval_seconds": 120
            }
        }
    }
    
    # Adjust based on performance
    changed = []
    
    if win_rate < 40:
        optimized_config['strategy']['volatility_filter']['adx_threshold'] = 40
        optimized_config['strategy']['volatility_filter']['multiplier'] = 3.5
        changed.append("ADX threshold: 30 → 40")
        changed.append("Vol multiplier: 2.5 → 3.5")
    elif win_rate < 50:
        optimized_config['strategy']['volatility_filter']['adx_threshold'] = 35
        optimized_config['strategy']['volatility_filter']['multiplier'] = 3.0
        changed.append("ADX threshold: 30 → 35")
        changed.append("Vol multiplier: 2.5 → 3.0")
    
    if profit_factor < 1.2:
        optimized_config['strategy']['volatility_filter']['tp_factor'] = 3.0
        optimized_config['strategy']['volatility_filter']['sl_factor'] = 0.8
        changed.append("TP factor: 2.0 → 3.0")
        changed.append("SL factor: 1.0 → 0.8")
    
    if trades_per_day > 100:
        optimized_config['strategy']['execution']['interval_seconds'] = 300
        optimized_config['strategy']['execution']['max_open_signals'] = 8
        optimized_config['strategy']['execution']['min_signal_gap_minutes'] = 20
        changed.append("Interval: 120s → 300s")
        changed.append("Max signals: 15 → 8")
        changed.append("Min gap: 0 → 20 minutes")
    elif trades_per_day > 50:
        optimized_config['strategy']['execution']['interval_seconds'] = 180
        optimized_config['strategy']['execution']['min_signal_gap_minutes'] = 10
        changed.append("Interval: 120s → 180s")
        changed.append("Min gap: 0 → 10 minutes")
    
    if len(losing_symbols) > 5:
        optimized_config['strategy']['blacklist_symbols'] = losing_symbols.head(5).index.tolist()
        changed.append(f"Blacklist: {len(losing_symbols.head(5))} symbols")
    
    if worst_strategy_profit < -5:
        optimized_config['strategy']['disabled_strategies'] = [worst_strategy_name]
        changed.append(f"Disabled: {worst_strategy_name}")
    
    if changed:
        print("\n📝 Các thay đổi được đề xuất:")
        for change in changed:
            print(f"   • {change}")
    
    print("\n" + json.dumps(optimized_config, indent=2))
    
    print(f"\n{'='*80}\n")
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_profit': total_profit,
        'max_drawdown': max_drawdown,
        'expectancy': expectancy,
        'rr_ratio': rr_ratio,
        'trades_per_day': trades_per_day,
        'issues': issues,
        'optimized_config': optimized_config,
        'df': closed_trades  # Return dataframe for further analysis
    }


if __name__ == "__main__":
    results = analyze_macd_bot('my_trades.csv')