"""
변동성 성장주(TSLA, NVDA)에 전략 재검증 — 모의투자 종목 선정
─────────────────────────────────────────────────────────
BTC에서 워크포워드를 통과한 추세필터·변동성 돌파가, 성장주에도 통하는가?
모의투자에 올리기 전 마지막 확인.

- 주식은 거래일 기준이라 학습 252일(1년) / 검증 63일(3개월)로 굴린다.
- 비교: 단순보유 vs 추세필터(워크포워드) vs 변동성돌파(워크포워드).
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

FEE, SLIPPAGE = 0.001, 0.0005
COST = FEE + SLIPPAGE
ROUNDTRIP = 2 * COST
IS_DAYS, OOS_DAYS = 252, 63
MA_CAND = [100, 150, 200, 250]
K_CAND = [0.3, 0.4, 0.5, 0.6, 0.7]
TICKERS = ["TSLA", "NVDA"]

def load(ticker, period="12y"):
    df = yf.download(ticker, period=period, interval="1d",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

def metrics(r):
    r = r.dropna()
    cum = (1 + r).cumprod()
    years = (r.index[-1] - r.index[0]).days / 365.25
    ann = len(r) / years
    cagr = cum.iloc[-1] ** (1 / years) - 1
    mdd = (cum / cum.cummax() - 1).min()
    sh = (r.mean() / r.std()) * np.sqrt(ann) if r.std() > 0 else 0
    return cum, cagr, mdd, sh

def sh_simple(r):                       # 워크포워드 선택용(같은 구간 비교라 연율화 불필요)
    return r.mean() / r.std() if r.std() > 0 else 0

def walkforward(ret_of, cands, index):
    wf = pd.Series(0.0, index=index)
    start = 0
    oos = None
    while start + IS_DAYS + OOS_DAYS <= len(index):
        isx = index[start : start + IS_DAYS]
        oos = index[start + IS_DAYS : start + IS_DAYS + OOS_DAYS]
        best = max(cands, key=lambda x: sh_simple(ret_of[x].loc[isx]))
        wf.loc[oos] = ret_of[best].loc[oos]
        start += OOS_DAYS
    first = index[IS_DAYS]
    return wf.loc[first:oos[-1]], first, oos[-1]

results = {}
for tk in TICKERS:
    df = load(tk)
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    mkt = c.pct_change().fillna(0)

    def trend_ret(n):
        pos = (c > c.rolling(n).mean()).astype(float).shift(1).fillna(0)
        return pos * mkt - pos.diff().abs().fillna(0) * COST

    def vb_ret(K):
        pr = h.shift(1) - l.shift(1)
        tg = o + K * pr
        en = (h >= tg) & (pr > 0)
        return (en.astype(float) * (c / tg - 1) - en.astype(float) * ROUNDTRIP).fillna(0)

    trend_of = {n: trend_ret(n) for n in MA_CAND}
    vb_of = {K: vb_ret(K) for K in K_CAND}

    tf_wf, first, last = walkforward(trend_of, MA_CAND, c.index)
    vb_wf, _, _ = walkforward(vb_of, K_CAND, c.index)
    bh = mkt.loc[first:last]

    results[tk] = {
        "period": (first.date(), last.date()),
        "Buy & Hold": metrics(bh),
        "Trend filter WF": metrics(tf_wf),
        "Vol. breakout WF": metrics(vb_wf),
    }

# ===== 출력 =====
for tk in TICKERS:
    r = results[tk]
    print(f"\n===== {tk}  (검증 {r['period'][0]} ~ {r['period'][1]}) =====")
    print(f"{'전략':<20}{'총수익':>10}{'CAGR':>8}{'MDD':>8}{'Sharpe':>9}")
    print("-" * 55)
    for name in ["Buy & Hold", "Trend filter WF", "Vol. breakout WF"]:
        cum, cagr, mdd, sh = r[name]
        print(f"{name:<20}{(cum.iloc[-1]-1)*100:>9.0f}%{cagr*100:>7.0f}%{mdd*100:>7.0f}%{sh:>9.2f}")

# ===== 차트 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, axes = plt.subplots(len(TICKERS), 1, figsize=(12, 5 * len(TICKERS)))
for ax, tk in zip(axes, TICKERS):
    r = results[tk]
    for name, color in [("Buy & Hold", "gray"),
                        ("Trend filter WF", "tab:green"),
                        ("Vol. breakout WF", "tab:orange")]:
        cum, cagr, mdd, sh = r[name]
        ax.plot(cum.index, cum, label=f"{name} (Sharpe {sh:.2f}, MDD {mdd*100:.0f}%)", color=color)
    ax.set_yscale("log")
    ax.set_title(f"{tk} — strategy walk-forward vs Buy & Hold (log scale)")
    ax.legend(); ax.grid(alpha=0.3, which="both")
plt.tight_layout()
out = os.path.join(HERE, "stock_validation.png")
plt.savefig(out, dpi=120)
print("\n차트 저장:", out)
