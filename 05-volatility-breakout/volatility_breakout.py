"""
트레이딩 봇 #5 — 변동성 돌파 전략 (래리 윌리엄스) 검증
─────────────────────────────────────────────────────
한국 퀀트 커뮤니티에서 가장 유명한 전략 중 하나. 우리 틀로 정직하게 거른다.

규칙:
  - 목표가 target = 오늘 시가 + K × (전일 고가 − 전일 저가)
  - 장중 고가가 target을 돌파하면 → target 가격에 매수(지정가 가정)
  - 당일 종가에 청산 (하루만 보유, 나머지 시간은 현금)
  - K(돌파 민감도)는 보통 0.5. 여기선 0.3~0.7을 스윕해 과최적화를 경계한다.

미래참조 없음: target은 '당일 시가 + 전일 변동폭'으로 장 시작에 확정,
              돌파는 장중, 청산은 종가. 매일 진입/청산이라 왕복 비용을 뗀다.

비교 대상: 단순 보유, 추세필터(>MA200).
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

FEE, SLIPPAGE = 0.001, 0.0005
ROUNDTRIP = 2 * (FEE + SLIPPAGE)   # 진입+청산(왕복)
COST = FEE + SLIPPAGE

# ===== 데이터 =====
data = yf.download("BTC-USD", period="8y", interval="1d",
                   auto_adjust=True, progress=False)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
data = data.dropna()
o, h, l, c = data["Open"], data["High"], data["Low"], data["Close"]
mkt = c.pct_change().fillna(0)

def metrics(r):
    cum = (1 + r).cumprod()
    years = len(r) / 365.25
    cagr = cum.iloc[-1] ** (1 / years) - 1
    mdd = (cum / cum.cummax() - 1).min()
    sharpe = (r.mean() / r.std()) * np.sqrt(365.25) if r.std() > 0 else 0
    return cum, cagr, mdd, sharpe

# ===== 변동성 돌파 일별 수익률 =====
def vb_returns(K):
    prev_range = h.shift(1) - l.shift(1)
    target = o + K * prev_range
    entered = (h >= target) & (prev_range > 0)        # 돌파 성공한 날만 거래
    gross = c / target - 1.0                          # target 매수 → 종가 청산
    ret = entered.astype(float) * gross - entered.astype(float) * ROUNDTRIP
    return ret.fillna(0), entered

# ===== 벤치마크 =====
bh_ret = mkt
tf_pos = (c > c.rolling(200).mean()).astype(float).shift(1).fillna(0)
tf_ret = tf_pos * mkt - tf_pos.diff().abs().fillna(0) * COST

print(f"데이터: {c.index[0].date()} ~ {c.index[-1].date()}  ({len(c)}일)\n")
print(f"{'전략':<26}{'총수익':>9}{'CAGR':>7}{'MDD':>7}{'Sharpe':>8}{'거래일%':>8}")
print("-" * 66)

def row(name, ret, exposure):
    cum, cagr, mdd, sh = metrics(ret)
    print(f"{name:<26}{(cum.iloc[-1]-1)*100:>8.0f}%{cagr*100:>6.0f}%{mdd*100:>6.0f}%{sh:>8.2f}{exposure*100:>7.0f}%")
    return cum

cum_bh = row("Buy & Hold", bh_ret, 1.0)
cum_tf = row("Trend filter (>MA200)", tf_ret, (tf_pos > 0).mean())

cum_vb = {}
for K in [0.3, 0.4, 0.5, 0.6, 0.7]:
    ret, entered = vb_returns(K)
    cum_vb[K] = row(f"Volatility breakout K={K}", ret, entered.mean())

print("\n* 거래일% = 시장에 노출된 날의 비율(낮을수록 현금으로 쉬는 시간 많음).")
print("* K를 바꿔도 결과가 들쭉날쭉하면 = 과최적화 위험(안정적이라야 신뢰).")

# ===== 차트 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(2, 1, figsize=(12, 9), gridspec_kw={"height_ratios": [2, 1]})

ax[0].plot(cum_bh.index, cum_bh, label="Buy & Hold", color="gray", lw=1.6)
ax[0].plot(cum_tf.index, cum_tf, label="Trend filter (>MA200)", color="tab:green", lw=1.4)
ax[0].plot(cum_vb[0.5].index, cum_vb[0.5], label="Volatility breakout K=0.5", color="tab:orange", lw=1.4)
ax[0].set_yscale("log")
ax[0].set_title("Volatility breakout vs Trend filter vs Buy & Hold (log scale), BTC 8y")
ax[0].legend(); ax[0].grid(alpha=0.3, which="both")

Ks = list(cum_vb.keys())
sharpes = [metrics(vb_returns(K)[0])[3] for K in Ks]
ax[1].bar([str(k) for k in Ks], sharpes, color="tab:orange", alpha=0.8)
ax[1].axhline(metrics(bh_ret)[3], color="gray", ls="--", label="Buy&Hold Sharpe")
ax[1].axhline(metrics(tf_ret)[3], color="tab:green", ls="--", label="Trend filter Sharpe")
ax[1].set_xlabel("K (breakout multiplier)"); ax[1].set_ylabel("Sharpe")
ax[1].set_title("Sharpe by K — stable across K = more trustworthy")
ax[1].legend(); ax[1].grid(alpha=0.3, axis="y")

plt.tight_layout()
out = os.path.join(HERE, "volatility_breakout.png")
plt.savefig(out, dpi=120)
print("차트 저장:", out)
