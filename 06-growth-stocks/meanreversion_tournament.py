"""
성장주(TSLA, NVDA) 평균회귀 전략 토너먼트 — 주식용 전략 발굴
─────────────────────────────────────────────────────────
추세필터/변동성돌파(하락 회피형)는 성장주에서 실패했다(상승을 놓침).
그래서 정반대 철학 = 평균회귀(눌림목 매수)를 시험한다.

후보:
  - 단순 보유 (벤치마크)
  - RSI(14): 과매도(<30) 매수, 회복(>55) 청산
  - 볼린저밴드: 하단(-2σ) 이탈 매수, 중심선(MA20) 회복 청산
  - 눌림목 매수: MA50 대비 -10% 하락 시 매수, MA50 회복 시 청산
  - (참고) 추세필터: 이미 실패했지만 대조용

목표: 단순보유를 '이긴다'가 아니라 '비슷하게 벌되 낙폭(MDD)을 줄인다'.
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

FEE, SLIPPAGE = 0.001, 0.0005
COST = FEE + SLIPPAGE
TICKERS = ["TSLA", "NVDA"]

def load(ticker, period="12y"):
    df = yf.download(ticker, period=period, interval="1d",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)

def state_position(close, buy_mask, sell_mask):
    """과매도 매수 / 회복 청산을 상태유지(ffill)로 포지션화"""
    raw = pd.Series(np.nan, index=close.index)
    raw[buy_mask] = 1.0
    raw[sell_mask] = 0.0
    return raw.ffill().fillna(0)

def metrics(r):
    r = r.dropna()
    cum = (1 + r).cumprod()
    years = (r.index[-1] - r.index[0]).days / 365.25
    ann = len(r) / years
    cagr = cum.iloc[-1] ** (1 / years) - 1
    mdd = (cum / cum.cummax() - 1).min()
    sh = (r.mean() / r.std()) * np.sqrt(ann) if r.std() > 0 else 0
    return cum, cagr, mdd, sh

def to_returns(pos, mkt):
    pos = pos.shift(1).fillna(0)
    return pos * mkt - pos.diff().abs().fillna(0) * COST

results = {}
for tk in TICKERS:
    df = load(tk)
    c = df["Close"]
    mkt = c.pct_change().fillna(0)

    strategies = {}
    strategies["Buy & Hold"] = pd.Series(1.0, index=c.index)

    r = rsi(c, 14)
    strategies["RSI mean-rev"] = state_position(c, r < 30, r > 55)

    mid = c.rolling(20).mean(); sd = c.rolling(20).std()
    strategies["Bollinger mean-rev"] = state_position(c, c < mid - 2 * sd, c > mid)

    ma50 = c.rolling(50).mean()
    strategies["Dip buy (MA50 -10%)"] = state_position(c, c < ma50 * 0.90, c > ma50)

    ma200 = c.rolling(200).mean()
    strategies["Trend filter (ref)"] = (c > ma200).astype(float)

    results[tk] = {name: metrics(to_returns(pos, mkt) if name != "Buy & Hold" else mkt)
                   for name, pos in strategies.items()}

# ===== 출력 =====
order = ["Buy & Hold", "RSI mean-rev", "Bollinger mean-rev", "Dip buy (MA50 -10%)", "Trend filter (ref)"]
for tk in TICKERS:
    print(f"\n===== {tk} =====")
    print(f"{'전략':<22}{'총수익':>10}{'CAGR':>8}{'MDD':>8}{'Sharpe':>9}")
    print("-" * 57)
    for name in order:
        cum, cagr, mdd, sh = results[tk][name]
        print(f"{name:<22}{(cum.iloc[-1]-1)*100:>9.0f}%{cagr*100:>7.0f}%{mdd*100:>7.0f}%{sh:>9.2f}")

# ===== 차트 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, axes = plt.subplots(len(TICKERS), 1, figsize=(12, 5 * len(TICKERS)))
for ax, tk in zip(axes, TICKERS):
    for name in order:
        cum, cagr, mdd, sh = results[tk][name]
        ax.plot(cum.index, cum, label=f"{name} (Sh {sh:.2f}, MDD {mdd*100:.0f}%)",
                lw=2.0 if name == "Buy & Hold" else 1.2)
    ax.set_yscale("log")
    ax.set_title(f"{tk} — mean-reversion strategies vs Buy & Hold (log)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3, which="both")
plt.tight_layout()
out = os.path.join(HERE, "meanreversion_tournament.png")
plt.savefig(out, dpi=120)
print("\n차트 저장:", out)
