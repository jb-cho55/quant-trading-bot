"""
BTC 추세필터(>MA_n) 워크포워드 정밀검증
─────────────────────────────────────────
앞선 토너먼트에서 추세필터가 좋아 보였지만, 그건 8년을 '한 번' 본 결과였다.
3편에서 배운 대로, 진짜 검증은 '창을 굴리며' 해야 한다.

방법:
  - 추세 기준선 후보: MA 100 / 150 / 200 / 250 일
  - 학습 1년(in-sample)에서 '위험조정수익(Sharpe)이 가장 높은' MA기간을 고른다.
  - 그 기준선으로 '다음 3개월(out-of-sample)'만 매매한다.
  - 3개월씩 굴리며 반복 → 이어붙인 실전 성적 vs 단순 보유 비교.

추가 관전 포인트:
  3편의 MA교차는 매번 '최적'이 바뀌어 16개 조합이 난립했다(엣지 없음).
  추세필터의 MA기간은 과연 안정적으로 한 곳에 쏠릴까? (쏠리면 = 진짜 엣지)
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

FEE, SLIPPAGE = 0.001, 0.0005
COST = FEE + SLIPPAGE
IS_DAYS, OOS_DAYS = 365, 90
MA_CANDIDATES = [100, 150, 200, 250]

# ===== 데이터 =====
data = yf.download("BTC-USD", period="8y", interval="1d",
                   auto_adjust=True, progress=False)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
data = data.dropna()
close = data["Close"]
mkt = close.pct_change().fillna(0)

def trend_daily(n):
    """MA n일 추세필터의 일별 전략수익 (비용 차감)"""
    pos = (close > close.rolling(n).mean()).astype(float).shift(1).fillna(0)
    trade = pos.diff().abs().fillna(0)
    return pos * mkt - trade * COST

ret_of = {n: trend_daily(n) for n in MA_CANDIDATES}

def sharpe(r):
    return (r.mean() / r.std()) * np.sqrt(365.25) if r.std() > 0 else 0

# ===== 워크포워드 루프 =====
wf = pd.Series(0.0, index=close.index)
picks = []
start = 0
oos_idx = None
while start + IS_DAYS + OOS_DAYS <= len(close):
    is_idx  = close.index[start : start + IS_DAYS]
    oos_idx = close.index[start + IS_DAYS : start + IS_DAYS + OOS_DAYS]
    # 학습구간 Sharpe 최고 MA기간 선택
    best = max(MA_CANDIDATES, key=lambda n: sharpe(ret_of[n].loc[is_idx]))
    wf.loc[oos_idx] = ret_of[best].loc[oos_idx]
    picks.append((oos_idx[0], best))
    start += OOS_DAYS

first, last = picks[0][0], oos_idx[-1]
wf_ret = wf.loc[first:last]
bh_ret = mkt.loc[first:last]

def metrics(r):
    cum = (1 + r).cumprod()
    years = len(r) / 365.25
    cagr = cum.iloc[-1] ** (1 / years) - 1
    mdd = (cum / cum.cummax() - 1).min()
    return cum, cagr, mdd, sharpe(r)

bh_cum, bh_cagr, bh_mdd, bh_sh = metrics(bh_ret)
wf_cum, wf_cagr, wf_mdd, wf_sh = metrics(wf_ret)

print(f"검증구간: {first.date()} ~ {last.date()}  ({len(wf_ret)}일, 재최적화 {len(picks)}회)")
print("=" * 56)
print(f"{'지표':<14}{'단순보유':>18}{'추세필터 WF':>18}")
print(f"{'총수익률':<14}{(bh_cum.iloc[-1]-1)*100:>17.1f}%{(wf_cum.iloc[-1]-1)*100:>17.1f}%")
print(f"{'연환산CAGR':<14}{bh_cagr*100:>17.1f}%{wf_cagr*100:>17.1f}%")
print(f"{'최대낙폭MDD':<14}{bh_mdd*100:>17.1f}%{wf_mdd*100:>17.1f}%")
print(f"{'샤프지수':<14}{bh_sh:>18.2f}{wf_sh:>18.2f}")
print("=" * 56)

# 뽑힌 MA기간 분포 (안정적이면 = 견고한 엣지)
uniq = {}
for _, n in picks:
    uniq[n] = uniq.get(n, 0) + 1
print("구간별로 선택된 추세 MA기간 분포 (한 곳에 쏠릴수록 안정적/견고):")
for n, c in sorted(uniq.items()):
    bar = "█" * c
    print(f"  MA {n:>3} : {c:>2}회 {bar}")

# ===== 차트 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(2, 1, figsize=(12, 9), gridspec_kw={"height_ratios": [2, 1]})
ax[0].plot(wf_cum.index, bh_cum, label=f"Buy & Hold (Sharpe {bh_sh:.2f}, MDD {bh_mdd*100:.0f}%)", color="gray")
ax[0].plot(wf_cum.index, wf_cum, label=f"Trend filter WF (Sharpe {wf_sh:.2f}, MDD {wf_mdd*100:.0f}%)", color="tab:green")
ax[0].set_yscale("log")
ax[0].set_title("BTC trend-filter walk-forward vs Buy & Hold (log scale)")
ax[0].legend(); ax[0].grid(alpha=0.3, which="both")

pick_dates = [p[0] for p in picks]
pick_ma = [p[1] for p in picks]
ax[1].step(pick_dates, pick_ma, where="post", color="tab:purple")
ax[1].set_ylabel("chosen MA period")
ax[1].set_yticks(MA_CANDIDATES)
ax[1].set_title("Re-selected trend MA per window (stable = real edge)")
ax[1].grid(alpha=0.3)
plt.tight_layout()
out = os.path.join(HERE, "walkforward_trend.png")
plt.savefig(out, dpi=120)
print("차트 저장:", out)
