"""
GTAA 스타일 멀티에셋 타이밍 (Meb Faber) — 인터넷 조사로 수립한 전략
─────────────────────────────────────────────────────────────
지금까지의 교훈: 추세 타이밍을 '개별 주식'에 쓰면 실패한다(노이즈·V자반등).
검증된 접근: 여러 '자산군'에 분산한 뒤 각각에 추세 타이밍을 건다.

전략:
  - 유니버스(5개 ETF): 미국주식(SPY)·외국주식(EFA)·미국채(IEF)·금(GLD)·부동산(VNQ)
  - 매월 말, 각 자산이 200일(10개월) 이동평균 '위'면 보유, '아래'면 현금
  - 보유 자산은 동일비중 (현금이면 그 몫은 쉬게 둔다)
비교: 동일가중 5자산 단순보유 / 주식 100%(SPY)
목표: 단순보유 대비 '낙폭을 크게 줄이면서 위험조정수익(Sharpe) 개선'
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

COST = 0.0015
ASSETS = ["SPY", "EFA", "IEF", "GLD", "VNQ"]

px = yf.download(ASSETS, period="max", interval="1d",
                 auto_adjust=True, progress=False)["Close"].dropna()
aret = px.pct_change().fillna(0)

# 200일선 위/아래 신호
above = (px > px.rolling(200).mean()).astype(float)

# 월말 신호 → 다음 달 보유 (월 1회 리밸런싱)
monthly_sig = above.resample("ME").last()
pos = monthly_sig.shift(1).reindex(px.index, method="ffill").fillna(0)

# 동일비중: 보유 신호가 켜진 자산에 1/N씩 (현금 슬롯은 0)
weight = pos / len(ASSETS)
strat_ret = (weight.shift(1) * aret).sum(axis=1)
turnover = (weight - weight.shift(1)).abs().sum(axis=1).fillna(0)
strat_ret = strat_ret - turnover * COST

# 벤치마크
ew_ret = aret.mean(axis=1)             # 동일가중 5자산 단순보유
spy_ret = aret["SPY"]                   # 주식 100%

start = px.index[210]                   # 200일 MA + 여유 이후부터 평가
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
    "GTAA timing": strat_ret,
    "Equal-weight hold": ew_ret,
    "S&P500 100% (SPY)": spy_ret,
}
print(f"검증: {start.date()} ~ {px.index[-1].date()}  (자산: {', '.join(ASSETS)})\n")
print(f"{'전략':<22}{'총수익':>10}{'CAGR':>8}{'MDD':>8}{'Sharpe':>9}")
print("-" * 57)
cums = {}
for name, r in series.items():
    cum, cagr, mdd, sh = metrics(r)
    cums[name] = cum
    print(f"{name:<22}{(cum.iloc[-1]-1)*100:>9.0f}%{cagr*100:>7.0f}%{mdd*100:>7.0f}%{sh:>9.2f}")

print("\n* 목표: 낙폭(MDD)을 크게 줄이면서 Sharpe가 단순보유 이상이면 성공.")

# ===== 차트 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(figsize=(12, 7))
for name, cum in cums.items():
    lw = 2.2 if name == "GTAA timing" else 1.3
    ax.plot(cum.index, cum, label=name, lw=lw)
ax.set_yscale("log")
ax.set_title("GTAA multi-asset timing vs buy & hold (log scale)")
ax.legend(); ax.grid(alpha=0.3, which="both")
plt.tight_layout()
out = os.path.join(HERE, "gtaa_timing.png")
plt.savefig(out, dpi=120)
print("차트 저장:", out)
