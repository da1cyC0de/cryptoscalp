"""
Price Data Fetcher untuk XAUUSD
Mengambil data harga real-time dari berbagai sumber
"""

import logging
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def fetch_xauusd_data(timeframe: str = "15m", lookback_days: int = 7) -> pd.DataFrame:
    """
    Ambil data XAUUSD dari Yahoo Finance.
    Ticker: GC=F (Gold Futures) sebagai proxy XAUUSD.
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

    tickers_to_try = ["GC=F", "XAUUSD=X"]

    for symbol in tickers_to_try:
        try:
            logger.info(f"📡 Mencoba ambil data dari {symbol}...")
            df = yf.download(
                symbol,
                period=f"{days}d",
                interval=interval,
                progress=False,
                auto_adjust=True,
            )

            if df is not None and not df.empty:
                # Handle multi-level columns dari yf.download
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                df.dropna(inplace=True)

                if not df.empty:
                    logger.info(f"✅ {symbol}: {len(df)} candle, "
                                f"harga terakhir: {df['Close'].iloc[-1]:.2f}, "
                                f"waktu: {df.index[-1]}")
                    return df

            logger.warning(f"⚠️ {symbol} kosong, coba ticker lain...")
        except Exception as e:
            logger.warning(f"⚠️ {symbol} error: {e}")
            continue

    logger.error("❌ Semua ticker gagal. Tidak bisa ambil data harga XAUUSD")
    return pd.DataFrame()


def get_current_price() -> float:
    """Ambil harga XAUUSD terkini"""
    try:
        df = yf.download("GC=F", period="1d", interval="1m", progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return float(df['Close'].iloc[-1])

        df = yf.download("XAUUSD=X", period="1d", interval="1m", progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return float(df['Close'].iloc[-1])

        return 0.0
    except Exception as e:
        logger.error(f"Error ambil harga terkini: {e}")
        return 0.0


def get_spread_estimate() -> float:
    """Estimasi spread dari bid-ask real-time"""
    try:
        ticker = yf.Ticker("GC=F")
        # fast_info lebih cepat dan up-to-date daripada .info
        bid = getattr(ticker, 'fast_info', {}).get('bid', 0)
        ask = getattr(ticker, 'fast_info', {}).get('ask', 0)
        if bid and ask and bid > 0 and ask > 0:
            spread = round(ask - bid, 2)
            if 0.01 < spread < 5.0:  # Sanity check
                return spread

        # Fallback ke .info
        info = ticker.info
        bid = info.get('bid', 0)
        ask = info.get('ask', 0)
        if bid and ask and bid > 0 and ask > 0:
            spread = round(ask - bid, 2)
            if 0.01 < spread < 5.0:
                return spread

        return 0.45
    except Exception:
        return 0.45
