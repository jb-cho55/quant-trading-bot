"""
모멘텀 로테이션(상대강도 + 절대모멘텀) — 주식용 전략 발굴 마지막 카드
─────────────────────────────────────────────────────────────
개별 종목에 베팅하지 않는다. 여러 성장주 바스켓에서 '최근 강한' 종목만
순환 보유한다(분산 + 추세 활용).

규칙:
  - 유니버스: 대형 기술주 8개
  - 매월 말, 최근 12개월 수익률 상위 3개를 동일비중 보유
  - 단, 수익률이 음수인 종목은 제외하고 그만큼 현금 (절대 모멘텀 = 하락 회피)
비교: 동일가중 바스켓 / S&P500(SPY) / (참고) NVDA 단독
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

COST = 0.0015
LOOKBACK = 252      # 12개월
TOP_K = 3
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "NFLX"]

raw = yf.download(TICKERS + ["SPY"], period="12y", interval="1d",
                  auto_adjust=True, progress=False)["Close"].dropna()
spy = raw["SPY"]
close = raw[TICKERS]
mret = close.pct_change().fillna(0)
mom = close.pct_change(LOOKBACK)                 # 각 시점의 12개월 수익률

# ===== 월말 리밸런싱 → 다음 달 비중 =====
period = close.index.to_period("M")
months = period.unique()
weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
for i in range(len(months) - 1):
    last_day = close.index[period == months[i]][-1]
    mvals = mom.loc[last_day].dropna()
    winners = mvals[mvals > 0].sort_values(ascending=False).index[:TOP_K]  # 절대+상대
    if len(winners) > 0:
        next_days = close.index[period == months[i + 1]]
        weights.loc[next_days, list(winners)] = 1.0 / TOP_K   # 나머지 슬롯은 현금
        picks_log = (months[i + 1], list(winners))

strat_ret = (weights.shift(1) * mret).sum(axis=1)
turnover = (weights - weights.shift(1)).abs().sum(axis=1).fillna(0)
strat_ret = strat_ret - turnover * COST

# 동일가중 바스켓(항상 8종목 보유), SPY, NVDA 단독
ew_ret = mret.mean(axis=1)
spy_ret = spy.pct_change().fillna(0)
nvda_ret = mret["NVDA"]

start = close.index[LOOKBACK + 21]              # 첫 리밸런싱 이후부터 평가
def metrics(r):
    r = r.loc[start:].dropna()
    cum = (1 + r).cumprod()
    years = (r.index[-1] - r.index[0]).days / 365.25
    ann = len(r) / years
    cagr = cum.iloc[-1] ** (1 / years) - 1
    mdd = (cum / cum.cummax() - 1).min()
    sh = (r.mean() / r.std()) * np.sqrt(ann) if r.std() > 0 else 0
    return cum, cagr, mdd, sh

series = {
    "Momentum rotation": strat_ret,
    "Equal-weight basket": ew_ret,
    "S&P500 (SPY)": spy_ret,
    "(ref) NVDA only": nvda_ret,
}

print(f"검증: {start.date()} ~ {close.index[-1].date()}\n")
print(f"{'전략':<22}{'총수익':>11}{'CAGR':>8}{'MDD':>8}{'Sharpe':>9}")
print("-" * 58)
cums = {}
for name, r in series.items():
    cum, cagr, mdd, sh = metrics(r)
    cums[name] = cum
    print(f"{name:<22}{(cum.iloc[-1]-1)*100:>10.0f}%{cagr*100:>7.0f}%{mdd*100:>7.0f}%{sh:>9.2f}")

print("\n* 공정 비교 상대는 '동일가중 바스켓'과 'SPY'. NVDA 단독은 사후편향이라 참고용.")

# ===== 차트 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(figsize=(12, 7))
for name, cum in cums.items():
    lw = 2.2 if name == "Momentum rotation" else 1.3
    ls = "--" if name.startswith("(ref)") else "-"
    ax.plot(cum.index, cum, label=name, lw=lw, ls=ls)
ax.set_yscale("log")
ax.set_title("Momentum rotation vs equal-weight / SPY / NVDA (log scale)")
ax.legend(); ax.grid(alpha=0.3, which="both")
plt.tight_layout()
out = os.path.join(HERE, "momentum_rotation.png")
plt.savefig(out, dpi=120)
print("차트 저장:", out)
