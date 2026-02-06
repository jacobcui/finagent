import os
import random
from typing import Callable, Optional


def _ensure_cache_env() -> str:
    # Use a writable cache directory under the backend folder by default.
    default_cache = os.path.join(os.path.dirname(__file__), ".yfcache")
    cache_dir = (
        os.getenv("YFINANCE_CACHE_DIR") or os.getenv("YF_CACHE_DIR") or default_cache
    )
    os.environ["YFINANCE_CACHE_DIR"] = cache_dir
    os.environ["YF_CACHE_DIR"] = cache_dir
    # Explicitly allow caching (set to "1" to disable).
    # We keep it enabled but point to a writable path.
    os.environ.setdefault("YF_CACHE_DISABLE", "0")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


_CACHE_DIR = _ensure_cache_env()

import pandas as pd  # noqa: E402
import yfinance as yf  # noqa: E402

ProgressCb = Callable[[float, str], None]


class YFinanceOp:
    """
    Wraps yfinance downloads with optional synthetic fallback via USE_SAMPLE_DATA env.
    """

    def __init__(
        self,
        progress_cb: Optional[ProgressCb] = None,
        use_sample: Optional[bool] = None,
    ):
        self.progress_cb = progress_cb or (lambda progress, message: None)
        if use_sample is None:
            self.use_sample = os.getenv("USE_SAMPLE_DATA") == "1"
        else:
            self.use_sample = use_sample
        # Ensure yfinance uses the writable cache dir.
        yf.set_tz_cache_location(_CACHE_DIR)

    def fetch(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        allow_fallback = (
            self.use_sample or os.getenv("ALLOW_SAMPLE_FALLBACK", "1") == "1"
        )
        try:
            data = yf.download(
                ticker,
                start=start,
                end=end,
                progress=False,
                auto_adjust=True,
                threads=False,
            )
        except Exception as exc:  # noqa: BLE001
            if allow_fallback:
                return self._sample_data(start, end, reason=str(exc))
            raise ValueError(f"Failed to download data for {ticker}: {exc}")

        if data is None or data.empty:
            if allow_fallback:
                return self._sample_data(start, end, reason="empty response")
            raise ValueError(
                f"No data returned for {ticker}. "
                "Check ticker spelling, date range, or network connectivity."
            )

        data.dropna(inplace=True)
        data.reset_index(inplace=True)
        if "Date" not in data.columns:
            # Ensure consistent column naming even when the index had no name
            # (e.g., mocked data)
            first_col = data.columns[0]
            data.rename(columns={first_col: "Date"}, inplace=True)
        return data

    def _sample_data(self, start: str, end: str, reason: str) -> pd.DataFrame:
        dates = pd.date_range(start=start, end=end, freq="B")
        price = 100.0
        rows = []
        for _ in dates:
            drift = random.uniform(-0.5, 0.7)
            price = max(5.0, price + drift)
            rows.append(price)
        data = pd.DataFrame({"Date": dates, "Close": rows})
        self.progress_cb(0.2, f"Using sample data ({reason})")
        return data
