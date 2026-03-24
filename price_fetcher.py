"""
Price Data Fetcher untuk XAUUSD
Mengambil harga spot dari TradingView (TVC:GOLD) dan
candle data dari Yahoo Finance (GC=F) yang di-adjust ke spot.
"""

import logging
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _get_spot_price_tradingview() -> float:
    """
    Ambil harga spot XAUUSD dari TradingView Scanner API (gratis, tanpa key).
    Ini harga yang sama persis dengan yang muncul di tradingview.com/symbols/XAUUSD
    """
    try:
        payload = {
            "symbols": {"tickers": ["TVC:GOLD"]},
            "columns": ["close"]
        }
        resp = requests.post(
            "https://scanner.tradingview.com/cfd/scan",
            json=payload,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("data") and len(data["data"]) > 0:
            price = float(data["data"][0]["d"][0])
            if price > 1000:
                logger.info(f"💰 TradingView spot (TVC:GOLD): {price:.2f}")
                return price
    except Exception as e:
        logger.warning(f"TradingView API error: {e}")
    return 0.0


def _get_live_price_gcf() -> float:
    """Ambil LIVE price GC=F dari Yahoo Finance (futures, harga lebih tinggi dari spot)"""
    try:
        ticker = yf.Ticker("GC=F")
        fi = ticker.fast_info
        price = fi.get("lastPrice", 0) or fi.get("regularMarketPrice", 0)
        if price and price > 1000:
            return float(price)
    except Exception as e:
        logger.warning(f"fast_info error: {e}")

    try:
        resp = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
            params={"interval": "1m", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        data = resp.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        if price and price > 1000:
            return float(price)
    except Exception as e:
        logger.warning(f"Yahoo chart API error: {e}")

    return 0.0


def fetch_xauusd_data(timeframe: str = "15m", lookback_days: int = 7) -> pd.DataFrame:
    """
    Ambil data candle XAUUSD.
    Candle dari GC=F (futures), tapi di-adjust ke harga spot dari TradingView.
    """
    interval_map = {
        '1m': ('1m', 1),
        '5m': ('5m', 5),
        '15m': ('15m', 30),
        '1h': ('1h', 60),
        '1d': ('1d', 365),
    }

    interval, max_days = interval_map.get(timeframe, ('15m', 30))
    days = min(lookback_days, max_days)

    try:
        logger.info("📡 Mengambil candle data dari GC=F...")
        df = yf.download(
            "GC=F",
            period=f"{days}d",
            interval=interval,
            progress=False,
            auto_adjust=True,
        )

        if df is None or df.empty:
            logger.error("❌ GC=F: data kosong")
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df.dropna(inplace=True)

        if df.empty:
            logger.error("❌ GC=F: data kosong setelah dropna")
            return pd.DataFrame()

        # Ambil live futures price (lebih real-time daripada candle terakhir)
        futures_live = _get_live_price_gcf()
        last_candle = float(df['Close'].iloc[-1])

        # Ambil harga spot dari TradingView
        spot = _get_spot_price_tradingview()

        if spot > 0 and futures_live > 0:
            # Adjust dari futures ke spot
            diff = futures_live - spot
            logger.info(f"📊 Futures live: {futures_live:.2f}, Spot: {spot:.2f}, "
                        f"Premium: {diff:.2f}, Candle terakhir: {last_candle:.2f}")

            # Shift seluruh candle: kurangi premium futures + koreksi stale candle
            total_shift = last_candle - spot
            if abs(total_shift) > 1:
                logger.info(f"🔧 Adjusting candle ke spot: shift={total_shift:.2f}")
                df['Open'] = df['Open'] - total_shift
                df['High'] = df['High'] - total_shift
                df['Low'] = df['Low'] - total_shift
                df['Close'] = df['Close'] - total_shift

        elif futures_live > 0:
            # TradingView gagal, minimal adjust ke live futures price
            diff = last_candle - futures_live
            if abs(diff) > 1:
                logger.info(f"🔧 Adjusting candle ke live futures: diff={diff:.2f}")
                df['Open'] = df['Open'] - diff
                df['High'] = df['High'] - diff
                df['Low'] = df['Low'] - diff
                df['Close'] = df['Close'] - diff

        # PENTING: Override harga candle terakhir pakai spot LIVE
        # Supaya entry price di signal = harga yang user lihat di chart
        spot_final = _get_spot_price_tradingview()
        if spot_final <= 0:
            spot_final = spot  # Pakai yang tadi kalau gagal
        if spot_final > 0:
            df.iloc[-1, df.columns.get_loc('Close')] = spot_final
            # Adjust High/Low kalau spot di luar range
            if spot_final > df.iloc[-1]['High']:
                df.iloc[-1, df.columns.get_loc('High')] = spot_final
            if spot_final < df.iloc[-1]['Low']:
                df.iloc[-1, df.columns.get_loc('Low')] = spot_final

        final_price = float(df['Close'].iloc[-1])
        logger.info(f"✅ Data siap: {len(df)} candle, harga final (LIVE): {final_price:.2f}")
        return df

    except Exception as e:
        logger.error(f"❌ GC=F error: {e}")
        return pd.DataFrame()


def get_current_price() -> float:
    """Ambil harga spot XAUUSD terkini"""
    # 1. TradingView (spot, paling akurat)
    spot = _get_spot_price_tradingview()
    if spot > 0:
        return spot

    # 2. Fallback ke GC=F live (futures)
    price = _get_live_price_gcf()
    if price > 0:
        logger.warning(f"⚠️ Pakai futures price: {price:.2f} (TradingView gagal)")
        return price

    return 0.0


def get_spread_estimate() -> float:
    """Estimasi spread dari bid-ask"""
    try:
        ticker = yf.Ticker("GC=F")
        fi = ticker.fast_info
        bid = fi.get("bid", 0)
        ask = fi.get("ask", 0)
        if bid and ask and bid > 1000 and ask > 1000:
            spread = round(ask - bid, 2)
            if 0.01 < spread < 5.0:
                return spread
    except Exception:
        pass
    return 0.45
