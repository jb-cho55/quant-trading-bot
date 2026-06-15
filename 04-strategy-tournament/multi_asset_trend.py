"""
추세필터(>200일선) 견고성 테스트 — 여러 자산에 동일 적용
─────────────────────────────────────────────────────
질문: 추세필터가 '비트코인에만 우연히' 맞은 걸까,
      아니면 자산을 가리지 않고 '덜 잃고 번다'가 통할까?

규칙(모든 자산 동일): 종가가 200일 이동평균 위면 보유(1), 아래면 현금(0).
                    다음날 진입(룩어헤드 방지), 매매일에 수수료+슬리피지 차감.
비교: 같은 자산 단순 보유(Buy & Hold) vs 추세필터.
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

FEE, SLIPPAGE = 0.001, 0.0005
COST = FEE + SLIPPAGE

assets = {
    "BTC":      "BTC-USD",
    "S&P500":   "SPY",
    "Nasdaq100":"QQQ",
    "Apple":    "AAPL",
    "Gold":     "GLD",
    "Samsung":  "005930.KS",
}

def stats(r):
    """일별 수익률 r → (CAGR, MDD, Sharpe). 연율화는 실제 거래일 밀도로 보정."""
    cum = (1 + r).cumprod()
    days = (r.index[-1] - r.index[0]).days
    years = days / 365.25
    ann = len(r) / years                       # 연간 거래일(주식 ~252, 코인 ~365)
    cagr = cum.iloc[-1] ** (1 / years) - 1
    mdd = (cum / cum.cummax() - 1).min()
    sharpe = (r.mean() / r.std()) * np.sqrt(ann) if r.std() > 0 else 0
    return cagr, mdd, sharpe

def evaluate(ticker):
    df = yf.download(ticker, period="max", interval="1d",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    close = df["Close"]
    mkt = close.pct_change().fillna(0)
    pos = (close > close.rolling(200).mean()).astype(float).shift(1).fillna(0)
    trade = pos.diff().abs().fillna(0)
    sret = pos * mkt - trade * COST
    return close.index[0].date(), stats(mkt), stats(sret)

rows = []
print(f"{'자산':<11}{'기간시작':>11} | {'[단순보유] CAGR  MDD  Sharpe':>30} | {'[추세필터] CAGR  MDD  Sharpe':>30}")
print("-" * 88)
for name, tk in assets.items():
    try:
        start, bh, tf = evaluate(tk)
        rows.append((name, bh, tf))
        print(f"{name:<11}{str(start):>11} | "
              f"{bh[0]*100:>8.0f}% {bh[1]*100:>5.0f}% {bh[2]:>6.2f}   | "
              f"{tf[0]*100:>8.0f}% {tf[1]*100:>5.0f}% {tf[2]:>6.2f}")
    except Exception as e:
        print(f"{name:<11} 데이터 오류: {e}")

# 요약: 추세필터가 보유 대비 'MDD 개선'·'Sharpe 개선'된 자산 수
mdd_better = sum(1 for _, bh, tf in rows if tf[1] > bh[1])      # 덜 빠짐(0에 가까움)
sharpe_better = sum(1 for _, bh, tf in rows if tf[2] > bh[2])
print("-" * 88)
print(f"추세필터가 단순보유보다 MDD(덜 잃음) 개선: {mdd_better}/{len(rows)}개 자산")
print(f"추세필터가 단순보유보다 Sharpe(효율) 개선: {sharpe_better}/{len(rows)}개 자산")

# ===== 차트: 자산별 Sharpe (보유 vs 추세필터) =====
HERE = os.path.dirname(os.path.abspath(__file__))
names = [r[0] for r in rows]
bh_sh = [r[1][2] for r in rows]
tf_sh = [r[2][2] for r in rows]
x = np.arange(len(names)); w = 0.38
fig, ax = plt.subplots(figsize=(11, 6))
ax.bar(x - w/2, bh_sh, w, label="Buy & Hold", color="gray")
ax.bar(x + w/2, tf_sh, w, label="Trend filter (>MA200)", color="tab:green")
ax.set_xticks(x); ax.set_xticklabels(names)
ax.set_ylabel("Sharpe ratio (higher = better risk-adjusted)")
ax.set_title("Trend filter vs Buy & Hold across assets — Sharpe ratio")
ax.legend(); ax.grid(alpha=0.3, axis="y")
plt.tight_layout()
out = os.path.join(HERE, "multi_asset_trend.png")
plt.savefig(out, dpi=120)
print("차트 저장:", out)
