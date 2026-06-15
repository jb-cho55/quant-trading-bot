"""
변동성 돌파 워크포워드 정밀검증
─────────────────────────────────────────
1차 백테스트에서 K=0.7이 환상적이었지만, 그건 '결과를 다 보고 고른' K였다.
진짜 질문: 과거 학습구간에서 고른 최적 K가, 한 번도 안 본 미래에도 통하는가?

방법(추세필터 검증과 동일 구조):
  - K 후보 [0.3, 0.4, 0.5, 0.6, 0.7]
  - 학습 1년에서 Sharpe 최고 K 선택 → 다음 3개월(미래)에 적용
  - 3개월씩 굴리며 반복 → 이어붙인 실전 성적 vs 단순보유.
  - 선택된 K가 안정적으로 한 곳에 쏠리는지(=진짜 엣지) 확인.
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

FEE, SLIPPAGE = 0.001, 0.0005
ROUNDTRIP = 2 * (FEE + SLIPPAGE)
COST = FEE + SLIPPAGE
IS_DAYS, OOS_DAYS = 365, 90
K_CANDIDATES = [0.3, 0.4, 0.5, 0.6, 0.7]

data = yf.download("BTC-USD", period="8y", interval="1d",
                   auto_adjust=True, progress=False)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
data = data.dropna()
o, h, l, c = data["Open"], data["High"], data["Low"], data["Close"]
mkt = c.pct_change().fillna(0)

def vb_returns(K):
    prev_range = h.shift(1) - l.shift(1)
    target = o + K * prev_range
    entered = (h >= target) & (prev_range > 0)
    gross = c / target - 1.0
    return (entered.astype(float) * gross - entered.astype(float) * ROUNDTRIP).fillna(0)

ret_of = {K: vb_returns(K) for K in K_CANDIDATES}

def sharpe(r):
    return (r.mean() / r.std()) * np.sqrt(365.25) if r.std() > 0 else 0

# ===== 워크포워드 루프 =====
wf = pd.Series(0.0, index=c.index)
picks = []
start = 0
oos_idx = None
while start + IS_DAYS + OOS_DAYS <= len(c):
    is_idx  = c.index[start : start + IS_DAYS]
    oos_idx = c.index[start + IS_DAYS : start + IS_DAYS + OOS_DAYS]
    best = max(K_CANDIDATES, key=lambda K: sharpe(ret_of[K].loc[is_idx]))
    wf.loc[oos_idx] = ret_of[best].loc[oos_idx]
    picks.append((oos_idx[0], best))
    start += OOS_DAYS

first, last = picks[0][0], oos_idx[-1]
wf_ret = wf.loc[first:last]
bh_ret = mkt.loc[first:last]
tf_pos = (c > c.rolling(200).mean()).astype(float).shift(1).fillna(0)
tf_ret = (tf_pos * mkt - tf_pos.diff().abs().fillna(0) * COST).loc[first:last]

def metrics(r):
    cum = (1 + r).cumprod()
    years = len(r) / 365.25
    cagr = cum.iloc[-1] ** (1 / years) - 1
    mdd = (cum / cum.cummax() - 1).min()
    return cum, cagr, mdd, sharpe(r)

print(f"검증구간: {first.date()} ~ {last.date()}  ({len(wf_ret)}일, 재최적화 {len(picks)}회)\n")
print(f"{'전략':<24}{'총수익':>9}{'CAGR':>7}{'MDD':>7}{'Sharpe':>8}")
print("-" * 56)
for name, r in [("Buy & Hold", bh_ret),
                ("Trend filter (>MA200)", tf_ret),
                ("Volatility breakout WF", wf_ret)]:
    cum, cagr, mdd, sh = metrics(r)
    print(f"{name:<24}{(cum.iloc[-1]-1)*100:>8.0f}%{cagr*100:>6.0f}%{mdd*100:>6.0f}%{sh:>8.2f}")

# 1차 백테스트에서 '최고'였던 K=0.7을 그대로 미래에 쓴 경우(과최적화 대조군)
naive07 = ret_of[0.7].loc[first:last]
cum, cagr, mdd, sh = metrics(naive07)
print(f"{'(참고) K=0.7 고정':<24}{(cum.iloc[-1]-1)*100:>8.0f}%{cagr*100:>6.0f}%{mdd*100:>6.0f}%{sh:>8.2f}")

print("\n구간별로 선택된 K 분포 (한 곳에 쏠릴수록 안정적/견고):")
uniq = {}
for _, K in picks:
    uniq[K] = uniq.get(K, 0) + 1
for K in K_CANDIDATES:
    cnt = uniq.get(K, 0)
    print(f"  K={K} : {cnt:>2}회 {'█' * cnt}")

# ===== 차트 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(2, 1, figsize=(12, 9), gridspec_kw={"height_ratios": [2, 1]})
cum_bh = (1 + bh_ret).cumprod()
cum_tf = (1 + tf_ret).cumprod()
cum_wf = (1 + wf_ret).cumprod()
ax[0].plot(cum_bh.index, cum_bh, label=f"Buy & Hold (Sharpe {sharpe(bh_ret):.2f})", color="gray")
ax[0].plot(cum_tf.index, cum_tf, label=f"Trend filter (Sharpe {sharpe(tf_ret):.2f})", color="tab:green")
ax[0].plot(cum_wf.index, cum_wf, label=f"Vol. breakout WF (Sharpe {sharpe(wf_ret):.2f})", color="tab:orange")
ax[0].set_yscale("log")
ax[0].set_title("Volatility breakout walk-forward vs benchmarks (log scale)")
ax[0].legend(); ax[0].grid(alpha=0.3, which="both")

pick_dates = [p[0] for p in picks]
pick_K = [p[1] for p in picks]
ax[1].step(pick_dates, pick_K, where="post", color="tab:orange")
ax[1].set_ylabel("chosen K"); ax[1].set_yticks(K_CANDIDATES)
ax[1].set_title("Re-selected K per window (jumpy = overfitting risk)")
ax[1].grid(alpha=0.3)
plt.tight_layout()
out = os.path.join(HERE, "walkforward_breakout.png")
plt.savefig(out, dpi=120)
print("차트 저장:", out)
