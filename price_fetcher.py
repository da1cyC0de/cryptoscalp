"""
Price Data Fetcher untuk XAUUSD
Mengambil data harga real-time dari Yahoo Finance (GC=F)
dengan koreksi ke harga spot menggunakan live price.
"""

import logging
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _get_live_price_gcf() -> float:
    """
    Ambil LIVE price GC=F dari Yahoo Finance fast_info.
    Ini lebih real-time daripada candle terakhir dari yf.download().
    """
    try:
        ticker = yf.Ticker("GC=F")
        fi = ticker.fast_info
        price = fi.get("lastPrice", 0) or fi.get("regularMarketPrice", 0)
        if price and price > 1000:
            return float(price)
    except Exception as e:
        logger.warning(f"fast_info error: {e}")

    # Fallback: Yahoo Chart API langsung
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
    Ambil data candle XAUUSD dari GC=F.
    Candle terakhir mungkin sudah stale (beda jam), jadi di-adjust
    ke live price supaya harga yang ditampilkan di sinyal akurat.

    Indikator teknikal (RSI, ADX, ATR, BB, MACD) tidak terpengaruh shifting
    karena dihitung dari perubahan relatif, bukan harga absolut.
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

        # Handle multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df.dropna(inplace=True)

        if df.empty:
            logger.error("❌ GC=F: data kosong setelah dropna")
            return pd.DataFrame()

        last_candle_close = float(df['Close'].iloc[-1])
        logger.info(f"📊 GC=F candle terakhir: {last_candle_close:.2f} ({df.index[-1]})")

        # Ambil LIVE price untuk mengkoreksi candle yang mungkin stale
        live_price = _get_live_price_gcf()
        if live_price > 0:
            diff = last_candle_close - live_price
            if abs(diff) > 1:
                logger.info(f"🔧 Adjusting candle ke live price: "
                            f"candle={last_candle_close:.2f}, live={live_price:.2f}, diff={diff:.2f}")
                df['Open'] = df['Open'] - diff
                df['High'] = df['High'] - diff
                df['Low'] = df['Low'] - diff
                df['Close'] = df['Close'] - diff

        final_price = float(df['Close'].iloc[-1])
        logger.info(f"✅ Data siap: {len(df)} candle, harga: {final_price:.2f}")
        return df

    except Exception as e:
        logger.error(f"❌ GC=F error: {e}")
        return pd.DataFrame()


def get_current_price() -> float:
    """Ambil harga XAUUSD terkini (live)"""
    price = _get_live_price_gcf()
    if price > 0:
        logger.info(f"💰 Live price: {price:.2f}")
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
