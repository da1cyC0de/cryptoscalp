"""
Price Data Fetcher untuk XAUUSD
Mengambil data harga real-time dari berbagai sumber
"""

import logging
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def fetch_xauusd_data(timeframe: str = "15m", lookback_days: int = 7) -> pd.DataFrame:
    """
    Ambil data XAUUSD dari Yahoo Finance.
    Ticker: GC=F (Gold Futures) sebagai proxy XAUUSD.
    
    Args:
        timeframe: interval candle (1m, 5m, 15m, 1h, 1d)
        lookback_days: berapa hari data ke belakang
        
    Returns:
        DataFrame dengan kolom Open, High, Low, Close, Volume
    """
    # Yahoo Finance interval mapping
    interval_map = {
        '1m': ('1m', 1),      # Max 7 hari untuk 1m
        '5m': ('5m', 5),      # Max 60 hari untuk 5m
        '15m': ('15m', 30),   # Max 60 hari untuk 15m
        '1h': ('1h', 60),     # Max 730 hari untuk 1h
        '1d': ('1d', 365),
    }

    interval, max_days = interval_map.get(timeframe, ('15m', 30))
    days = min(lookback_days, max_days)

    try:
        ticker = yf.Ticker("GC=F")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=interval
        )

        if df.empty:
            logger.warning("Data dari GC=F kosong, mencoba XAUUSD=X...")
            ticker = yf.Ticker("XAUUSD=X")
            df = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval
            )

        if df.empty:
            logger.error("Tidak bisa mengambil data harga XAUUSD")
            return pd.DataFrame()

        # Bersihkan kolom
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df.dropna(inplace=True)

        logger.info(f"✅ Berhasil ambil {len(df)} candle XAUUSD ({interval})")
        return df

    except Exception as e:
        logger.error(f"❌ Error mengambil data harga: {e}")
        return pd.DataFrame()


def get_current_price() -> float:
    """Ambil harga XAUUSD terkini"""
    try:
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])

        ticker = yf.Ticker("XAUUSD=X")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])

        return 0.0
    except Exception as e:
        logger.error(f"Error ambil harga terkini: {e}")
        return 0.0


def get_spread_estimate() -> float:
    """Estimasi spread dari bid-ask (simplified)"""
    try:
        ticker = yf.Ticker("GC=F")
        info = ticker.info
        bid = info.get('bid', 0)
        ask = info.get('ask', 0)
        if bid > 0 and ask > 0:
            return round(ask - bid, 2)
        return 0.30  # Default spread estimate
    except Exception:
        return 0.30
