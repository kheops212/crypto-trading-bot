"""
Streamlit dashboard — strategy performance comparison + trade notifications.
Run: streamlit run dashboard.py
"""
import time
import warnings
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import vectorbt as vbt

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*requires frequency.*")

import config
import trades as tr

st.set_page_config(
    page_title="Crypto Bot Dashboard",
    page_icon="📈",
    layout="wide",
)

STRATEGIES = ["ema_crossover", "rsi_reversal", "macd_crossover", "bollinger_reversion", "combined"]

LEVEL_ICON = {"success": "🟢", "warning": "🟡", "error": "🔴", "info": "🔵"}
LEVEL_COLOR = {"success": "#1a7a4a", "warning": "#7a6a1a", "error": "#7a1a1a", "info": "#1a3a7a"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

_FIAT = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"}


def to_yf_ticker(symbol: str) -> str:
    if "/" not in symbol:
        return symbol  # stock
    base, quote = symbol.split("/")
    if base in _FIAT and quote in _FIAT:
        return f"{base}{quote}=X"  # forex: EUR/USD → EURUSD=X
    quote = "USD" if quote in ("USDT", "BUSD") else quote
    return f"{base}-{quote}"       # crypto: BTC/USDT → BTC-USD


def color_pnl(val):
    if pd.isna(val):
        return ""
    return "color: #1a7a4a; font-weight:bold" if val >= 0 else "color: #c0392b; font-weight:bold"


@st.cache_data(ttl=60)
def fetch_live_price(symbol: str) -> float:
    import yfinance as yf
    ticker = to_yf_ticker(symbol)
    data = yf.download(ticker, period="1d", interval="5m", auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return float(data["Close"].iloc[-1]) if not data.empty else 0.0


@st.cache_data(ttl=3600)
def load_price_data(yf_ticker: str, period: str, interval: str) -> pd.Series:
    return vbt.YFData.download(yf_ticker, period=period, interval=interval).get("Close")


def build_signals(price: pd.Series, strategy: str) -> tuple[pd.Series, pd.Series]:
    df = pd.DataFrame({"close": price})

    if strategy == "ema_crossover":
        df["fast"] = ta.ema(df["close"], length=config.EMA_FAST)
        df["slow"] = ta.ema(df["close"], length=config.EMA_SLOW)
        entries = (df["fast"] > df["slow"]) & (df["fast"].shift(1) <= df["slow"].shift(1))
        exits = (df["fast"] < df["slow"]) & (df["fast"].shift(1) >= df["slow"].shift(1))

    elif strategy == "rsi_reversal":
        df["rsi"] = ta.rsi(df["close"], length=config.RSI_PERIOD)
        entries = (df["rsi"] >= config.RSI_OVERSOLD) & (df["rsi"].shift(1) < config.RSI_OVERSOLD)
        exits = (df["rsi"] <= config.RSI_OVERBOUGHT) & (df["rsi"].shift(1) > config.RSI_OVERBOUGHT)

    elif strategy == "macd_crossover":
        macd = ta.macd(df["close"], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
        df["macd"] = macd.filter(like="MACD_").iloc[:, 0]
        df["sig"] = macd.filter(like="MACDs_").iloc[:, 0]
        entries = (df["macd"] > df["sig"]) & (df["macd"].shift(1) <= df["sig"].shift(1))
        exits = (df["macd"] < df["sig"]) & (df["macd"].shift(1) >= df["sig"].shift(1))

    elif strategy == "bollinger_reversion":
        bb = ta.bbands(df["close"], length=config.BB_PERIOD, std=config.BB_STD)
        df["lower"] = bb.filter(like="BBL_").iloc[:, 0]
        df["upper"] = bb.filter(like="BBU_").iloc[:, 0]
        entries = df["close"] < df["lower"]
        exits = df["close"] > df["upper"]

    elif strategy == "combined":
        macd = ta.macd(df["close"], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
        df["macd"] = macd.filter(like="MACD_").iloc[:, 0]
        df["sig"] = macd.filter(like="MACDs_").iloc[:, 0]
        df["rsi"] = ta.rsi(df["close"], length=config.RSI_PERIOD)
        macd_up = (df["macd"] > df["sig"]) & (df["macd"].shift(1) <= df["sig"].shift(1))
        macd_dn = (df["macd"] < df["sig"]) & (df["macd"].shift(1) >= df["sig"].shift(1))
        entries = macd_up & (df["rsi"] < config.RSI_OVERBOUGHT)
        exits = macd_dn & (df["rsi"] > config.RSI_OVERSOLD)

    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # Trend filter: suppress buy entries when price is below 200 EMA
    if config.TREND_FILTER:
        ema200 = ta.ema(df["close"], length=config.TREND_EMA_PERIOD)
        in_uptrend = df["close"] > ema200
        entries = entries & in_uptrend

    return entries.fillna(False), exits.fillna(False)


@st.cache_data(ttl=3600)
def run_all_backtests(yf_ticker: str, period: str, interval: str) -> pd.DataFrame:
    price = load_price_data(yf_ticker, period, interval)
    rows = []
    for strat in STRATEGIES:
        try:
            entries, exits = build_signals(price, strat)
            pf = vbt.Portfolio.from_signals(price, entries, exits, init_cash=1000, fees=0.001)
            stats = pf.stats()
            rows.append({
                "Strategy": strat,
                "Total Return %": round(stats["Total Return [%]"], 2),
                "Sharpe Ratio": round(stats.get("Sharpe Ratio", 0) or 0, 3),
                "Max Drawdown %": round(stats["Max Drawdown [%]"], 2),
                "Win Rate %": round(stats.get("Win Rate [%]", 0) or 0, 2),
                "# Trades": int(stats["Total Trades"]),
            })
        except Exception as e:
            rows.append({
                "Strategy": strat,
                "Total Return %": None,
                "Sharpe Ratio": None,
                "Max Drawdown %": None,
                "Win Rate %": None,
                "# Trades": None,
            })
    return pd.DataFrame(rows).set_index("Strategy")


def equity_curves(yf_ticker: str, period: str, interval: str) -> dict[str, pd.Series]:
    price = load_price_data(yf_ticker, period, interval)
    curves = {}
    for strat in STRATEGIES:
        try:
            entries, exits = build_signals(price, strat)
            pf = vbt.Portfolio.from_signals(price, entries, exits, init_cash=1000, fees=0.001)
            curves[strat] = pf.value()
        except Exception:
            pass
    return curves


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Bot Settings")
    all_symbols = config.SYMBOLS + config.STOCK_SYMBOLS + config.FOREX_SYMBOLS
    backtest_symbol = st.selectbox("Backtest symbol", all_symbols, index=0)
    yf_ticker = to_yf_ticker(backtest_symbol)
    period = st.selectbox("Backtest period", ["1mo", "3mo", "6mo", "1y"], index=3)
    interval = st.selectbox("Interval", ["1h", "4h", "1d"], index=0)
    auto_refresh = st.toggle("Auto-refresh (30s)", value=False)
    if st.button("Clear notification cache"):
        tr.mark_notifications_seen()
        st.success("Marked all as seen.")
    st.divider()
    st.markdown(
        "[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/YOUR_USERNAME)",
        unsafe_allow_html=False,
    )
    st.divider()
    st.caption(f"Active strategy: **{config.STRATEGY}**")
    st.caption(f"Crypto: **{', '.join(config.SYMBOLS)}**")
    st.caption(f"Stocks: **{', '.join(config.STOCK_SYMBOLS) if config.STOCK_SYMBOLS else 'none'}**")
    st.caption(f"Forex: **{', '.join(config.FOREX_SYMBOLS) if config.FOREX_SYMBOLS else 'none'}**")
    st.caption(f"Trend filter: **{'200 EMA' if config.TREND_FILTER else 'off'}**")
    st.caption(f"Paper trade: **{config.PAPER_TRADE}**")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

unseen = tr.unseen_count()
badge = f" ({unseen} new)" if unseen > 0 else ""
open_pos = tr.get_all_open_positions()
pos_badge = f" ({len(open_pos)})" if open_pos else ""
st.title("Crypto Trading Bot Dashboard")

tab_perf, tab_opt, tab_pnl, tab_pos, tab_notify, tab_trades = st.tabs([
    "Strategy Performance",
    "Optimize RSI",
    "P&L Summary",
    f"Positions{pos_badge}",
    f"Notifications{badge}",
    "Trade History",
])


# ---------------------------------------------------------------------------
# Tab 1: Strategy Performance
# ---------------------------------------------------------------------------

with tab_perf:
    st.subheader("Backtest Comparison")
    st.caption(f"Symbol: {backtest_symbol} | Period: {period} | Interval: {interval} | $1,000 starting capital | 0.1% fees")

    with st.spinner("Running backtests..."):
        df_stats = run_all_backtests(yf_ticker, period, interval)

    # Color-coded metrics table
    def color_return(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        color = "#1a7a4a" if val > 0 else "#7a1a1a"
        return f"color: {color}; font-weight: bold"

    def color_dd(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        severity = min(val / 50, 1.0)
        r = int(120 + severity * 100)
        return f"color: rgb({r}, 50, 50)"

    styled = (
        df_stats.style
        .map(color_return, subset=["Total Return %"])
        .map(color_dd, subset=["Max Drawdown %"])
        .format({
            "Total Return %": lambda v: f"{v:+.2f}%" if pd.notna(v) else "—",
            "Sharpe Ratio": lambda v: f"{v:.3f}" if pd.notna(v) else "—",
            "Max Drawdown %": lambda v: f"{v:.2f}%" if pd.notna(v) else "—",
            "Win Rate %": lambda v: f"{v:.2f}%" if pd.notna(v) else "—",
            "# Trades": lambda v: str(int(v)) if pd.notna(v) else "—",
        })
    )
    st.dataframe(styled, width='stretch')

    # Bar chart: Total Return
    st.subheader("Total Return by Strategy")
    fig_bar = px.bar(
        df_stats.reset_index(),
        x="Strategy",
        y="Total Return %",
        color="Total Return %",
        color_continuous_scale=["#7a1a1a", "#555", "#1a7a4a"],
        color_continuous_midpoint=0,
        text="Total Return %",
    )
    fig_bar.update_traces(texttemplate="%{text:+.2f}%", textposition="outside")
    fig_bar.update_layout(showlegend=False, coloraxis_showscale=False, height=350)
    st.plotly_chart(fig_bar, width='stretch')

    # Equity curves
    st.subheader("Equity Curves")
    with st.spinner("Building equity curves..."):
        curves = equity_curves(yf_ticker, period, interval)

    fig_eq = go.Figure()
    for strat, curve in curves.items():
        fig_eq.add_trace(go.Scatter(
            x=curve.index,
            y=curve.values,
            name=strat,
            mode="lines",
        ))
    fig_eq.update_layout(
        yaxis_title="Portfolio Value ($)",
        xaxis_title="Date",
        height=420,
        hovermode="x unified",
    )
    st.plotly_chart(fig_eq, width='stretch')

    # Sharpe vs Drawdown scatter
    st.subheader("Risk / Reward")
    valid = df_stats.dropna()
    if not valid.empty:
        fig_rr = px.scatter(
            valid.reset_index(),
            x="Max Drawdown %",
            y="Sharpe Ratio",
            text="Strategy",
            size="# Trades",
            color="Total Return %",
            color_continuous_scale=["#7a1a1a", "#555", "#1a7a4a"],
            color_continuous_midpoint=0,
        )
        fig_rr.update_traces(textposition="top center")
        fig_rr.update_layout(height=380)
        st.plotly_chart(fig_rr, width='stretch')


# ---------------------------------------------------------------------------
# Tab 2: Optimize RSI
# ---------------------------------------------------------------------------

@st.cache_data(ttl=7200, show_spinner=False)
def run_rsi_optimization(yf_ticker: str, period: str, interval: str) -> pd.DataFrame:
    price = load_price_data(yf_ticker, period, interval).squeeze()
    df_base = pd.DataFrame({"close": price})
    ema200 = ta.ema(df_base["close"], length=config.TREND_EMA_PERIOD)
    in_uptrend = df_base["close"] > ema200

    rsi_periods   = [7, 10, 14, 18, 21]
    oversolds     = [20, 25, 30, 35, 40]
    overboughts   = [60, 65, 70, 75, 80]

    rows = []
    for rp in rsi_periods:
        rsi = ta.rsi(df_base["close"], length=rp)
        for ob in overboughts:
            for os_ in oversolds:
                if os_ >= ob:
                    continue
                entries = (rsi >= os_) & (rsi.shift(1) < os_)
                exits   = (rsi <= ob)  & (rsi.shift(1) > ob)
                if config.TREND_FILTER:
                    entries = entries & in_uptrend
                entries = entries.fillna(False)
                exits   = exits.fillna(False)
                if entries.sum() == 0:
                    continue
                try:
                    pf = vbt.Portfolio.from_signals(price, entries, exits, init_cash=1000, fees=0.001)
                    s  = pf.stats()
                    rows.append({
                        "RSI Period":  rp,
                        "Oversold":    os_,
                        "Overbought":  ob,
                        "Return %":    round(s["Total Return [%]"], 2),
                        "Win Rate %":  round(s.get("Win Rate [%]") or 0, 2),
                        "Max DD %":    round(s["Max Drawdown [%]"], 2),
                        "Trades":      int(s["Total Trades"]),
                    })
                except Exception:
                    pass
    return pd.DataFrame(rows)


with tab_opt:
    st.subheader("RSI Parameter Optimization")
    st.caption(
        f"Symbol: {backtest_symbol} | Period: {period} | "
        f"Trend filter: {'on (200 EMA)' if config.TREND_FILTER else 'off'} | "
        f"Grid: 5 RSI periods × 5 oversold × 5 overbought levels"
    )

    with st.spinner("Running optimization grid (this may take ~30s)..."):
        df_opt = run_rsi_optimization(yf_ticker, period, interval)

    if df_opt.empty:
        st.warning("No valid parameter combinations produced trades. Try a longer period.")
    else:
        # Best combos table
        st.subheader("Top 10 Combinations by Win Rate")
        top10 = (
            df_opt.sort_values("Win Rate %", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        top10.index += 1

        def hl_best(s):
            return ["background-color: #1a3a1a" if s.name == 1 else "" for _ in s]

        st.dataframe(
            top10.style
            .apply(hl_best, axis=1)
            .format({
                "Return %":   "{:+.2f}%",
                "Win Rate %": "{:.2f}%",
                "Max DD %":   "{:.2f}%",
            }),
            width='stretch',
        )

        best = top10.iloc[0]
        st.success(
            f"Best combo: RSI period **{int(best['RSI Period'])}** | "
            f"Oversold **{int(best['Oversold'])}** | "
            f"Overbought **{int(best['Overbought'])}** → "
            f"Win rate **{best['Win Rate %']:.1f}%** | "
            f"Return **{best['Return %']:+.2f}%** | "
            f"Max DD **{best['Max DD %']:.1f}%**"
        )

        st.code(
            f"# Paste into config.py to apply best settings\n"
            f"RSI_PERIOD    = {int(best['RSI Period'])}\n"
            f"RSI_OVERSOLD  = {int(best['Oversold'])}\n"
            f"RSI_OVERBOUGHT = {int(best['Overbought'])}",
            language="python",
        )

        st.divider()

        # Heatmap: Win Rate % for best RSI period
        best_period = int(best["RSI Period"])
        df_heat = df_opt[df_opt["RSI Period"] == best_period].copy()

        st.subheader(f"Win Rate % Heatmap — RSI Period {best_period}")
        pivot_wr = df_heat.pivot_table(index="Oversold", columns="Overbought", values="Win Rate %")
        fig_wr = px.imshow(
            pivot_wr,
            color_continuous_scale=["#7a1a1a", "#555", "#1a7a4a"],
            text_auto=".1f",
            labels={"x": "Overbought", "y": "Oversold", "color": "Win Rate %"},
            aspect="auto",
        )
        fig_wr.update_layout(height=350)
        st.plotly_chart(fig_wr, width='stretch')

        # Heatmap: Return % for best RSI period
        st.subheader(f"Return % Heatmap — RSI Period {best_period}")
        pivot_ret = df_heat.pivot_table(index="Oversold", columns="Overbought", values="Return %")
        fig_ret = px.imshow(
            pivot_ret,
            color_continuous_scale=["#7a1a1a", "#555", "#1a7a4a"],
            color_continuous_midpoint=0,
            text_auto=".1f",
            labels={"x": "Overbought", "y": "Oversold", "color": "Return %"},
            aspect="auto",
        )
        fig_ret.update_layout(height=350)
        st.plotly_chart(fig_ret, width='stretch')

        # RSI period bar chart
        st.subheader("Win Rate % by RSI Period (best oversold/overbought per period)")
        df_by_period = (
            df_opt.sort_values("Win Rate %", ascending=False)
            .groupby("RSI Period")
            .first()
            .reset_index()
        )
        fig_period = px.bar(
            df_by_period,
            x="RSI Period",
            y="Win Rate %",
            color="Win Rate %",
            color_continuous_scale=["#7a1a1a", "#555", "#1a7a4a"],
            text="Win Rate %",
        )
        fig_period.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_period.update_layout(showlegend=False, coloraxis_showscale=False, height=320)
        st.plotly_chart(fig_period, width='stretch')


# ---------------------------------------------------------------------------
# Tab 3: P&L Summary
# ---------------------------------------------------------------------------

with tab_pnl:
    st.subheader("Realized P&L Summary")
    closed = tr.get_closed_positions(limit=1000)
    open_positions_pnl = tr.get_all_open_positions()

    if not closed:
        st.info("No closed positions yet. P&L will appear here once the bot starts trading.")
    else:
        df_closed = pd.DataFrame(closed)
        df_closed["pnl"] = (df_closed["close_price"] - df_closed["entry_price"]) * df_closed["amount"]
        df_closed["pnl_pct"] = (df_closed["close_price"] / df_closed["entry_price"] - 1) * 100
        df_closed["closed_at"] = pd.to_datetime(df_closed["closed_at"])
        df_closed["asset_class"] = df_closed["symbol"].apply(
            lambda s: "Forex" if "/" in s and s.split("/")[1] in {"USD","EUR","GBP","JPY","AUD","CAD","CHF","NZD"}
            else ("Stock" if "/" not in s else "Crypto")
        )

        # --- Top metrics ---
        total_pnl   = df_closed["pnl"].sum()
        total_trades = len(df_closed)
        wins        = (df_closed["pnl"] >= 0).sum()
        win_rate    = wins / total_trades * 100
        avg_win     = df_closed[df_closed["pnl"] >= 0]["pnl"].mean() if wins > 0 else 0
        avg_loss    = df_closed[df_closed["pnl"] < 0]["pnl"].mean() if (total_trades - wins) > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

        # Period filters
        now = pd.Timestamp.utcnow().tz_localize(None)
        this_week  = df_closed[df_closed["closed_at"].dt.tz_localize(None) >= now - pd.Timedelta(days=7)]["pnl"].sum()
        this_month = df_closed[df_closed["closed_at"].dt.tz_localize(None) >= now - pd.Timedelta(days=30)]["pnl"].sum()

        # Unrealized P&L placeholder (fetched live in positions tab)
        unrealized = sum(
            (fetch_live_price(p["symbol"]) - p["entry_price"]) * p["amount"]
            for p in open_positions_pnl
        ) if open_positions_pnl else 0.0

        # Row 1 — headline metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Realized P&L", f"${total_pnl:+.2f}")
        c2.metric("This Month", f"${this_month:+.2f}")
        c3.metric("This Week", f"${this_week:+.2f}")
        c4.metric("Unrealized P&L", f"${unrealized:+.2f}")

        # Row 2 — trade stats
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Trades", total_trades)
        c2.metric("Win Rate", f"{win_rate:.1f}%")
        c3.metric("Avg Win", f"${avg_win:+.2f}")
        c4.metric("Profit Factor", f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞")

        st.divider()

        # --- Cumulative P&L chart ---
        st.subheader("Cumulative Realized P&L Over Time")
        df_sorted = df_closed.sort_values("closed_at").copy()
        df_sorted["cumulative_pnl"] = df_sorted["pnl"].cumsum()
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=df_sorted["closed_at"],
            y=df_sorted["cumulative_pnl"],
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color="#1a7a4a" if total_pnl >= 0 else "#c0392b", width=2),
            fillcolor="rgba(26,122,74,0.1)" if total_pnl >= 0 else "rgba(192,57,43,0.1)",
            name="Cumulative P&L",
        ))
        fig_cum.update_layout(
            yaxis_title="Cumulative P&L ($)",
            xaxis_title="Date",
            height=350,
            hovermode="x unified",
        )
        fig_cum.add_hline(y=0, line_dash="dash", line_color="#555")
        st.plotly_chart(fig_cum, width='stretch')

        # --- P&L by asset class ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("P&L by Asset Class")
            by_class = df_closed.groupby("asset_class")["pnl"].sum().reset_index()
            fig_class = px.bar(
                by_class, x="asset_class", y="pnl",
                color="pnl",
                color_continuous_scale=["#7a1a1a", "#555", "#1a7a4a"],
                color_continuous_midpoint=0,
                text="pnl",
            )
            fig_class.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
            fig_class.update_layout(showlegend=False, coloraxis_showscale=False,
                                    height=300, xaxis_title="", yaxis_title="P&L ($)")
            st.plotly_chart(fig_class, width='stretch')

        with col2:
            st.subheader("P&L by Symbol (Top 10)")
            by_sym = df_closed.groupby("symbol")["pnl"].sum().sort_values().tail(10).reset_index()
            fig_sym = px.bar(
                by_sym, x="pnl", y="symbol", orientation="h",
                color="pnl",
                color_continuous_scale=["#7a1a1a", "#555", "#1a7a4a"],
                color_continuous_midpoint=0,
            )
            fig_sym.update_layout(showlegend=False, coloraxis_showscale=False,
                                  height=300, xaxis_title="P&L ($)", yaxis_title="")
            st.plotly_chart(fig_sym, width='stretch')

        # --- Close reason breakdown ---
        st.subheader("Exit Reason Breakdown")
        by_reason = df_closed.groupby("close_reason").agg(
            Trades=("pnl", "count"),
            Total_PnL=("pnl", "sum"),
            Avg_PnL=("pnl", "mean"),
            Win_Rate=("pnl", lambda x: (x >= 0).mean() * 100),
        ).reset_index().rename(columns={"close_reason": "Reason"})

        def color_reason(val):
            colors = {"take_profit": "color:#1a7a4a;font-weight:bold",
                      "stop_loss": "color:#c0392b;font-weight:bold",
                      "strategy_signal": "color:#7a6a1a;font-weight:bold"}
            return colors.get(val, "")

        st.dataframe(
            by_reason.style
            .map(color_reason, subset=["Reason"])
            .map(color_pnl, subset=["Total_PnL", "Avg_PnL"])
            .format({"Total_PnL": "${:+.2f}", "Avg_PnL": "${:+.2f}", "Win_Rate": "{:.1f}%"}),
            width='stretch',
        )

        # --- Available to withdraw ---
        st.divider()
        st.subheader("Available to Withdraw")
        col1, col2 = st.columns(2)
        col1.metric("Realized profits (all-time)", f"${max(total_pnl, 0):.2f}",
                    help="Only realized (closed) profits. Does not include open positions.")
        col2.metric("50% harvest suggestion", f"${max(total_pnl, 0) * 0.5:.2f}",
                    help="Common approach: withdraw half, leave half to compound.")


# ---------------------------------------------------------------------------
# Tab 4: Positions

# ---------------------------------------------------------------------------



with tab_pos:
    st.subheader("Open Positions")
    open_positions = tr.get_all_open_positions()

    if not open_positions:
        st.info("No open positions. The bot will open one when the strategy fires a buy signal.")
    else:
        rows = []
        for p in open_positions:
            price = fetch_live_price(p["symbol"])
            pnl = (price - p["entry_price"]) * p["amount"]
            pnl_pct = (price / p["entry_price"] - 1) * 100 if p["entry_price"] else 0
            highest = p.get("highest_price") or p["entry_price"]
            trail_stop = highest * (1 - config.STOP_LOSS_PCT)
            sl_dist = (price - trail_stop) / price * 100
            tp_dist = (p["take_profit"] - price) / price * 100
            trail_moved = (highest / p["entry_price"] - 1) * 100
            opened = p["opened_at"][:19].replace("T", " ")
            rows.append({
                "Symbol": p["symbol"],
                "Amount": p["amount"],
                "Entry $": p["entry_price"],
                "Current $": price,
                "High $": highest,
                "Trail Stop $": trail_stop,
                "Take Profit $": p["take_profit"],
                "Stop dist %": sl_dist,
                "TP dist %": tp_dist,
                "Trail moved %": trail_moved,
                "Unreal. P&L $": pnl,
                "Unreal. P&L %": pnl_pct,
                "Opened": opened,
            })

        df_pos = pd.DataFrame(rows)

        styled_pos = (
            df_pos.style
            .map(color_pnl, subset=["Unreal. P&L $", "Unreal. P&L %", "Trail moved %"])
            .format({
                "Amount": "{:.6f}",
                "Entry $": "${:,.2f}",
                "Current $": "${:,.2f}",
                "High $": "${:,.2f}",
                "Trail Stop $": "${:,.2f}",
                "Take Profit $": "${:,.2f}",
                "Stop dist %": "{:.2f}%",
                "TP dist %": "{:.2f}%",
                "Trail moved %": "{:+.2f}%",
                "Unreal. P&L $": "{:+.4f}",
                "Unreal. P&L %": "{:+.2f}%",
            })
        )
        st.dataframe(styled_pos, width='stretch')

        total_pnl = sum(r["Unreal. P&L $"] for r in rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("Open Positions", len(open_positions))
        c2.metric("Total Unrealized P&L", f"${total_pnl:+.4f}")
        c3.metric("Active Strategy", config.STRATEGY)

    st.divider()
    st.subheader("Closed Positions")
    closed = tr.get_closed_positions(limit=50)

    if not closed:
        st.info("No closed positions yet.")
    else:
        closed_rows = []
        for p in closed:
            pnl = (p["close_price"] - p["entry_price"]) * p["amount"]
            pnl_pct = (p["close_price"] / p["entry_price"] - 1) * 100 if p["entry_price"] else 0
            closed_rows.append({
                "Symbol": p["symbol"],
                "Amount": p["amount"],
                "Entry $": p["entry_price"],
                "Close $": p["close_price"],
                "P&L $": pnl,
                "P&L %": pnl_pct,
                "Reason": p["close_reason"],
                "Opened": p["opened_at"][:19].replace("T", " "),
                "Closed": p["closed_at"][:19].replace("T", " "),
            })

        df_closed = pd.DataFrame(closed_rows)

        def color_reason(val):
            colors = {
                "take_profit": "color: #1a7a4a; font-weight:bold",
                "stop_loss": "color: #c0392b; font-weight:bold",
                "strategy_signal": "color: #7a6a1a; font-weight:bold",
            }
            return colors.get(val, "")

        styled_closed = (
            df_closed.style
            .map(color_pnl, subset=["P&L $", "P&L %"])
            .map(color_reason, subset=["Reason"])
            .format({
                "Amount": "{:.6f}",
                "Entry $": "${:,.2f}",
                "Close $": "${:,.2f}",
                "P&L $": "{:+.4f}",
                "P&L %": "{:+.2f}%",
            })
        )
        st.dataframe(styled_closed, width='stretch')

        total_realized = sum(r["P&L $"] for r in closed_rows)
        wins = sum(1 for r in closed_rows if r["P&L $"] >= 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Closed Trades", len(closed_rows))
        c2.metric("Total Realized P&L", f"${total_realized:+.4f}")
        c3.metric("Win Rate", f"{wins / len(closed_rows) * 100:.1f}%")


# ---------------------------------------------------------------------------
# Tab 3: Notifications
# ---------------------------------------------------------------------------

with tab_notify:
    st.subheader("Trade Notifications")
    notifications = tr.get_notifications(limit=100)

    if not notifications:
        st.info("No notifications yet. Notifications appear here when the bot executes trades.")
    else:
        tr.mark_notifications_seen()
        for n in notifications:
            icon = LEVEL_ICON.get(n["level"], "🔵")
            bg = LEVEL_COLOR.get(n["level"], "#1a3a7a")
            ts = n["timestamp"][:19].replace("T", " ")
            st.markdown(
                f"""
                <div style="
                    background:{bg}22;
                    border-left: 4px solid {bg};
                    border-radius: 6px;
                    padding: 10px 14px;
                    margin-bottom: 8px;
                ">
                    <span style="font-size:1.1em">{icon} <strong>{n['title']}</strong></span>
                    &nbsp;&nbsp;<span style="color:#888;font-size:0.85em">{ts} UTC</span>
                    <br><span style="color:#ccc">{n['body']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Tab 4: Trade History
# ---------------------------------------------------------------------------

with tab_trades:
    st.subheader("Trade History")
    trade_list = tr.get_trades()

    if not trade_list:
        st.info("No trades logged yet.")
    else:
        df_trades = pd.DataFrame(trade_list)
        df_trades["timestamp"] = df_trades["timestamp"].str[:19].str.replace("T", " ")
        df_trades["value_usdt"] = (df_trades["amount"] * df_trades["price"]).round(2)

        def color_side(val):
            return "color: #1a7a4a; font-weight:bold" if val == "buy" else "color: #c0392b; font-weight:bold"

        styled_trades = (
            df_trades[["timestamp", "symbol", "side", "amount", "price", "value_usdt", "reason"]]
            .style
            .map(color_side, subset=["side"])
            .format({"amount": "{:.6f}", "price": "${:,.2f}", "value_usdt": "${:,.2f}"})
        )
        st.dataframe(styled_trades, width='stretch')

        # Summary metrics
        buys = df_trades[df_trades["side"] == "buy"]
        sells = df_trades[df_trades["side"] == "sell"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Trades", len(df_trades))
        col2.metric("Buys", len(buys))
        col3.metric("Sells", len(sells))


# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------

if auto_refresh:
    time.sleep(30)
    st.rerun()
