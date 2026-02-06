from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st


# 详细注释：汇率锁价引擎核心类
class ExchangeRateLockEngine:
    def __init__(self):
        # RBA公开汇率API端点（澳元兑主要货币历史数据）
        self.RBA_API_URL = (
            "https://www.rba.gov.au/statistics/frequency/exchange-rates.html"
        )
        # 备用API（RBA CSV数据端点）
        self.RBA_CSV_URL = (
            "https://www.rba.gov.au/statistics/frequency/exchange-rates.csv"
        )
        # 目标货币对映射
        self.CURRENCY_PAIRS = {"USD": "AUD/USD", "CNY": "AUD/CNY"}

    # 详细注释：获取RBA近30天汇率数据（处理API请求失败）
    def get_rba_exchange_rates(self, target_currency: str = "USD") -> pd.DataFrame:
        try:
            # 尝试从RBA CSV端点获取数据
            response = requests.get(self.RBA_CSV_URL, timeout=15)
            response.raise_for_status()

            # 解析CSV数据（处理RBA特殊格式）
            from io import StringIO

            csv_data = StringIO(response.text)
            # RBA CSV usually has header info, skipping rows might be needed.
            # The prompt code suggested skiprows=10, which is typical for RBA.
            df = pd.read_csv(csv_data, skiprows=10, index_col=0, parse_dates=True)

            # 筛选目标货币对（AUD兑目标货币，RBA数据为1澳元兑换的外币数量）
            # The column names in RBA CSV are usually series IDs like 'FXRUSD',
            # but sometimes descriptive.
            # However, assuming the prompt code logic is correct or I need to verify.
            # RBA CSV columns often have series IDs.
            # If the user provided code assumes specific structure, I will use it.
            # But I should probably add a check or fallback if columns are not found.
            # For now, I will stick to the user provided code structure but maybe
            # add column detection logic if I can.
            # The provided code does: currency_col =
            # self.CURRENCY_PAIRS[target_currency]
            # This implies the CSV has columns named "AUD/USD" or "AUD/CNY".
            # RBA CSV usually has "A$1=USD" or similar description in rows above header?
            # Actually, standard RBA CSV has series IDs.
            # Let's assume the user code provided in summary is what they want,
            # or I should improve it.
            # I'll stick to the provided code but wrap it in try/except for column
            # access.

            # If explicit mapping fails, try to find relevant column
            target_col = self.CURRENCY_PAIRS.get(target_currency)
            if target_col not in df.columns:
                # Try to find a column that looks like it
                candidates = [c for c in df.columns if target_currency in str(c)]
                if candidates:
                    target_col = candidates[0]

            if target_col and target_col in df.columns:
                df = df[[target_col]].dropna()
            else:
                # If we can't find the column, raise to trigger simulation
                raise ValueError(f"Column for {target_currency} not found in RBA data")

            # 获取近30天数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            # Filter by date index
            df = df.sort_index()
            df = df.loc[start_date:end_date]

            return df

        except Exception as e:
            st.error(
                f"RBA汇率API请求失败或数据解析错误：{str(e)}，将使用模拟数据进行演示"
            )
            # 生成模拟数据（用于API故障时的 fallback）
            dates = pd.date_range(end=datetime.now(), periods=30)
            # Base rate roughly 0.65 for USD, 4.7 for CNY
            base = 0.65 if target_currency == "USD" else 4.7
            simulated_rates = np.random.normal(base, base * 0.02, 30)
            return pd.DataFrame(
                {self.CURRENCY_PAIRS[target_currency]: simulated_rates}, index=dates
            )

    # 详细注释：计算汇率统计指标（均值、标准差、波动幅度）
    def calculate_rate_statistics(self, rate_df: pd.DataFrame) -> dict:
        rate_series = rate_df.iloc[:, 0]
        mean_rate = rate_series.mean()
        std_rate = rate_series.std()
        max_rate = rate_series.max()
        min_rate = rate_series.min()
        # 计算波动幅度（相对于均值的百分比）
        volatility = (std_rate / mean_rate) * 100

        return {
            "mean": round(mean_rate, 4),
            "std": round(std_rate, 4),
            "volatility": round(volatility, 2),
            "max": round(max_rate, 4),
            "min": round(min_rate, 4),
            "current": round(rate_series.iloc[-1], 4),
            "history": rate_series.tolist(),
        }

    # 详细注释：生成锁价建议（波动超过±2%时触发提醒）
    def generate_lock_suggestion(
        self, rate_df: pd.DataFrame, stats: dict, payment_cycle: int, amount: float
    ) -> str:
        currency_pair = rate_df.columns[0]
        if stats["volatility"] > 2:
            # 预测未来周期汇率趋势
            trend = "跌破" if stats["current"] < stats["mean"] else "突破"
            threshold = round(
                stats["mean"] * (0.98 if stats["current"] < stats["mean"] else 1.02), 4
            )
            return (
                f"⚠️ 汇率波动警告（{stats['volatility']}% > 2%）\n"
                f"未来{payment_cycle}天{currency_pair}大概率{trend}{threshold}\n"
                f"建议立即锁价，锁定金额{amount}澳元对应的{round(amount * stats['current'], 2)}目标货币"
            )
        else:
            return (
                f"✅ 汇率稳定（波动{stats['volatility']}% ≤ 2%）\n"
                f"当前{currency_pair}汇率{stats['current']}，均值{stats['mean']}\n"
                f"未来{payment_cycle}天无需紧急锁价"
            )

    # 详细注释：Streamlit折线图可视化（标注历史最优锁价点和当前汇率）
    def visualize_rate_trend(self, rate_df: pd.DataFrame, stats: dict):
        st.line_chart(rate_df, use_container_width=True)
        # 标注历史最优锁价点（最高汇率点）
        max_date = rate_df.idxmax().iloc[0]
        st.markdown(
            f"📌 历史最优锁价点：{max_date.strftime('%Y-%m-%d')} {stats['max']}"
        )
        # 标注当前汇率位置
        current_date = rate_df.index[-1]
        st.markdown(
            f"🔍 当前汇率位置：{current_date.strftime('%Y-%m-%d')} {stats['current']}"
        )


# 详细注释：Streamlit前端交互界面
def app():
    # Only set page config if it hasn't been set
    # (simple check logic not available, relying on wrapper)
    # st.set_page_config is removed from here for integration safety
    st.title("跨境金融智能体 - 汇率锁价引擎")

    # 初始化引擎
    engine = ExchangeRateLockEngine()

    # 输入参数配置
    # Use object notation for sidebar to avoid context issues in some versions but
    # 'with' is fine
    with st.sidebar:
        st.header("输入参数配置")
        payment_cycle = st.number_input(
            "用户收付周期（天）", min_value=1, max_value=30, value=7
        )
        target_currency = st.selectbox("目标货币", ["USD", "CNY"], index=0)
        transaction_amount = st.number_input(
            "交易金额（澳元）", min_value=100.0, max_value=100000.0, value=10000.0
        )
        fetch_btn = st.button("获取汇率数据并分析")

    # 处理用户请求
    if fetch_btn:
        with st.spinner("正在获取RBA汇率数据并分析..."):
            # 获取汇率数据
            rate_df = engine.get_rba_exchange_rates(target_currency)
            # 计算统计指标
            stats = engine.calculate_rate_statistics(rate_df)
            # 生成锁价建议
            suggestion = engine.generate_lock_suggestion(
                rate_df, stats, payment_cycle, transaction_amount
            )

            # 展示结果
            st.subheader("汇率分析结果")
            st.write(suggestion)
            st.subheader("近30天汇率趋势图")
            engine.visualize_rate_trend(rate_df, stats)
            st.subheader("汇率统计指标")
            st.table(pd.DataFrame(stats, index=[0]))


if __name__ == "__main__":
    st.set_page_config(page_title="跨境金融智能体 - 汇率锁价引擎", page_icon="💱")
    app()
