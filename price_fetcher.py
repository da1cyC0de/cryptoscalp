"""
Price Data Fetcher untuk XAUUSD
Mengambil data harga SPOT real-time dari berbagai sumber
"""

import logging
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _fetch_spot_price_metals_live() -> float:
    """Ambil harga spot gold real-time dari metals.live (gratis, tanpa API key)"""
    try:
        resp = requests.get("https://api.metals.live/v1/spot", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for item in data:
            if item.get("gold"):
                price = float(item["gold"])
                if price > 1000:
                    return price
        return 0.0
    except Exception as e:
        logger.warning(f"metals.live error: {e}")
        return 0.0


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

    # Prioritaskan XAUUSD=X (spot) daripada GC=F (futures, harga lebih tinggi)
    tickers_to_try = ["XAUUSD=X", "GC=F"]

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
                    last_price = float(df['Close'].iloc[-1])

                    # Jika pakai GC=F (futures), adjust ke spot price
                    if symbol == "GC=F":
                        spot = _fetch_spot_price_metals_live()
                        if spot > 0:
                            diff = last_price - spot
                            if abs(diff) > 5:  # Ada selisih signifikan
                                logger.info(f"🔧 Adjusting GC=F ke spot: futures={last_price:.2f}, spot={spot:.2f}, diff={diff:.2f}")
                                df['Open'] = df['Open'] - diff
                                df['High'] = df['High'] - diff
                                df['Low'] = df['Low'] - diff
                                df['Close'] = df['Close'] - diff
                                last_price = float(df['Close'].iloc[-1])

                    logger.info(f"✅ {symbol}: {len(df)} candle, "
                                f"harga terakhir: {last_price:.2f}, "
                                f"waktu: {df.index[-1]}")
                    return df

            logger.warning(f"⚠️ {symbol} kosong, coba ticker lain...")
        except Exception as e:
            logger.warning(f"⚠️ {symbol} error: {e}")
            continue

    logger.error("❌ Semua ticker gagal. Tidak bisa ambil data harga XAUUSD")
    return pd.DataFrame()


def get_current_price() -> float:
    """Ambil harga SPOT XAUUSD terkini dari berbagai sumber"""

    # 1. Coba metals.live API dulu (spot price paling akurat)
    spot = _fetch_spot_price_metals_live()
    if spot > 0:
        logger.info(f"💰 Harga spot dari metals.live: {spot:.2f}")
        return spot

    # 2. Fallback ke XAUUSD=X (spot) dari Yahoo Finance
    try:
        df = yf.download("XAUUSD=X", period="1d", interval="1m", progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            price = float(df['Close'].iloc[-1])
            logger.info(f"💰 Harga spot dari XAUUSD=X: {price:.2f}")
            return price
    except Exception as e:
        logger.warning(f"XAUUSD=X error: {e}")

    # 3. Fallback terakhir ke GC=F (futures)
    try:
        df = yf.download("GC=F", period="1d", interval="1m", progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            price = float(df['Close'].iloc[-1])
            logger.warning(f"⚠️ Pakai harga futures GC=F: {price:.2f} (mungkin lebih tinggi dari spot)")
            return price
    except Exception as e:
        logger.warning(f"GC=F error: {e}")

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
