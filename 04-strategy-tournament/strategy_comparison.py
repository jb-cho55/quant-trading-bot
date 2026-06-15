"""
트레이딩 봇 #4 — 전략 토너먼트: '덜 잃는' 전략 찾기
─────────────────────────────────────────────────
1~3편 결론: 단순 이동평균으로 '총수익'에서 단순 보유를 이기긴 어렵다.
그래서 목표를 바꾼다 → "비슷하게 벌되 훨씬 덜 잃는다" = 위험조정수익으로 이기기.

같은 기간(BTC 8년)·같은 비용으로 4개 전략을 비교한다.
측정: 총수익 / CAGR / 최대낙폭(MDD) / 샤프지수 / MAR(=CAGR/MDD).
  - 샤프지수: 변동성 1단위당 수익 (높을수록 '효율적')
  - MAR: 낙폭 1단위당 수익 (높을수록 '덜 잃고 번다')
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

FEE, SLIPPAGE = 0.001, 0.0005
COST = FEE + SLIPPAGE

# ===== 데이터 =====
data = yf.download("BTC-USD", period="8y", interval="1d",
                   auto_adjust=True, progress=False)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
data = data.dropna()
close = data["Close"]
mkt = close.pct_change().fillna(0)          # 시장(일별) 수익률

def apply_position(pos):
    """포지션(0/1) 시리즈 → 비용 차감한 일별 전략수익률"""
    pos = pos.shift(1).fillna(0)            # 다음날 진입(룩어헤드 방지)
    trade = pos.diff().abs().fillna(0)
    return pos * mkt - trade * COST

# ===== 전략 4종 (각각 '보유=1 / 현금=0' 포지션을 정의) =====
strategies = {}

# 1) 단순 보유
strategies["Buy & Hold"] = pd.Series(1.0, index=close.index)

# 2) MA 교차 20/50 (1편)
ma_s, ma_l = close.rolling(20).mean(), close.rolling(50).mean()
strategies["MA cross 20/50"] = (ma_s > ma_l).astype(float)

# 3) 추세 필터: 200일선 위면 보유, 아래면 현금
ma200 = close.rolling(200).mean()
strategies["Trend filter (>MA200)"] = (close > ma200).astype(float)

# 4) 절대 모멘텀: 최근 90일 수익률이 +면 보유, -면 현금
mom = close.pct_change(90)
strategies["Abs. momentum (90d)"] = (mom > 0).astype(float)

# ===== 성과 지표 =====
def metrics(sret):
    cum = (1 + sret).cumprod()
    total = cum.iloc[-1] - 1
    cagr = cum.iloc[-1] ** (365.25 / len(cum)) - 1
    mdd = (cum / cum.cummax() - 1).min()
    sharpe = (sret.mean() / sret.std()) * np.sqrt(365.25) if sret.std() > 0 else 0
    mar = cagr / abs(mdd) if mdd != 0 else 0
    return cum, total, cagr, mdd, sharpe, mar

print(f"데이터: {close.index[0].date()} ~ {close.index[-1].date()}  ({len(close)}일)\n")
print(f"{'전략':<24}{'총수익':>9}{'CAGR':>8}{'MDD':>8}{'Sharpe':>8}{'MAR':>7}")
print("-" * 64)

cums = {}
for name, pos in strategies.items():
    sret = apply_position(pos)
    cum, total, cagr, mdd, sharpe, mar = metrics(sret)
    cums[name] = cum
    print(f"{name:<24}{total*100:>8.0f}%{cagr*100:>7.0f}%{mdd*100:>7.0f}%{sharpe:>8.2f}{mar:>7.2f}")

print("\n* Sharpe·MAR이 높을수록 '위험 대비 효율'이 좋음(덜 잃고 번다).")

# ===== 차트: 누적수익(로그축) =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(figsize=(12, 7))
for name, cum in cums.items():
    lw = 2.2 if name == "Buy & Hold" else 1.4
    ax.plot(cum.index, cum, label=name, linewidth=lw)
ax.set_yscale("log")
ax.set_title("Strategy tournament — cumulative return (log scale), BTC 8y")
ax.set_ylabel("growth of 1.0 (log)")
ax.legend(); ax.grid(alpha=0.3, which="both")
plt.tight_layout()
out = os.path.join(HERE, "strategy_tournament.png")
plt.savefig(out, dpi=120)
print("차트 저장:", out)
