"""
비트코인 이동평균 교차(MA Crossover) 전략 백테스트
─────────────────────────────────────────────
* 실거래 없음: 과거 데이터로 전략을 '시뮬레이션'만 합니다. 자금 위험 0.
* 전략: 단기 이동평균(20일)이 장기 이동평균(50일)을 위로 뚫으면 매수(보유),
        아래로 뚫으면 매도(현금). 흔히 '골든크로스 / 데드크로스'라 부릅니다.
* 비교 대상: 그냥 사서 들고 있기 (Buy & Hold)
* 트레이딩 봇 블로그 시리즈 #1 예제
"""
import os
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# ===== 설정 =====
TICKER = "BTC-USD"
PERIOD = "3y"          # 최근 3년 일봉
SHORT, LONG = 20, 50   # 이동평균 기간 (단기 / 장기)
FEE = 0.001            # 거래 수수료 0.1% (매수·매도 시 차감)

# ===== 1. 데이터 다운로드 =====
print(f"[1/4] {TICKER} 데이터 다운로드 중...")
data = yf.download(TICKER, period=PERIOD, interval="1d",
                   auto_adjust=True, progress=False)
# yfinance가 컬럼을 2단(MultiIndex)으로 줄 때가 있어 1단으로 평탄화
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
data = data.dropna()
print(f"      {len(data)}일치 ({data.index[0].date()} ~ {data.index[-1].date()})")

# ===== 2. 이동평균 & 매매 신호 =====
print("[2/4] 이동평균 계산 및 신호 생성...")
data["MA_s"] = data["Close"].rolling(SHORT).mean()
data["MA_l"] = data["Close"].rolling(LONG).mean()
# 단기 > 장기 이면 1(보유), 아니면 0(현금)
data["signal"] = (data["MA_s"] > data["MA_l"]).astype(int)
# 신호는 '다음 날' 진입: 오늘 종가를 보고 내일 매매 → 미래참조(룩어헤드) 방지
data["position"] = data["signal"].shift(1).fillna(0)

# ===== 3. 수익률 계산 (수수료 포함) =====
print("[3/4] 수익률 계산...")
data["mkt_ret"] = data["Close"].pct_change().fillna(0)
# 포지션이 바뀌는 날 = 거래 발생 → 그날 수수료 차감
data["trade"] = data["position"].diff().abs().fillna(0)
data["strat_ret"] = data["position"] * data["mkt_ret"] - data["trade"] * FEE
# 누적 수익 (시작값 1.0)
data["bh_cum"] = (1 + data["mkt_ret"]).cumprod()
data["strat_cum"] = (1 + data["strat_ret"]).cumprod()

# ===== 4. 성과 지표 =====
def cagr(cum):           # 연환산 수익률
    years = len(cum) / 365.25
    return cum.iloc[-1] ** (1 / years) - 1

def mdd(cum):            # 최대 낙폭 (고점 대비 최대 하락)
    return (cum / cum.cummax() - 1).min()

n_trades = int(data["trade"].sum())
print("[4/4] 결과")
print("=" * 46)
print(f"{'지표':<14}{'매수보유':>15}{'MA전략':>15}")
print("-" * 46)
print(f"{'총수익률':<14}{(data['bh_cum'].iloc[-1]-1)*100:>14.1f}%{(data['strat_cum'].iloc[-1]-1)*100:>14.1f}%")
print(f"{'연환산CAGR':<14}{cagr(data['bh_cum'])*100:>14.1f}%{cagr(data['strat_cum'])*100:>14.1f}%")
print(f"{'최대낙폭MDD':<14}{mdd(data['bh_cum'])*100:>14.1f}%{mdd(data['strat_cum'])*100:>14.1f}%")
print("=" * 46)
print(f"전략 거래 횟수: {n_trades}회 (수수료 {FEE*100:.1f}%/회 반영)")

# ===== 차트 저장 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(2, 1, figsize=(12, 9))
ax[0].plot(data.index, data["Close"], label="BTC Close", color="black", lw=0.8)
ax[0].plot(data.index, data["MA_s"], label=f"MA{SHORT}", color="tab:blue", lw=1)
ax[0].plot(data.index, data["MA_l"], label=f"MA{LONG}", color="tab:red", lw=1)
ax[0].set_title("BTC-USD price & moving averages")
ax[0].legend(); ax[0].grid(alpha=0.3)
ax[1].plot(data.index, data["bh_cum"], label="Buy & Hold", color="gray")
ax[1].plot(data.index, data["strat_cum"], label="MA strategy", color="tab:green")
ax[1].set_title("Cumulative return (start = 1.0)")
ax[1].legend(); ax[1].grid(alpha=0.3)
plt.tight_layout()
out = os.path.join(HERE, "backtest_result.png")
plt.savefig(out, dpi=120)
print(f"차트 저장: {out}")
