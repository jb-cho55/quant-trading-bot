"""
트레이딩 봇 #3 — 워크포워드 분석(Walk-Forward Analysis)
─────────────────────────────────────────────────────
2편에서는 데이터를 '전반부/후반부'로 딱 한 번만 잘라서 검증했습니다.
하지만 시장은 계속 변합니다. 한 번 정한 파라미터가 5년 내내 최적일 리 없죠.

워크포워드 분석은 이렇게 합니다:
  1) 최근 1년(학습구간)에서 최적 이동평균 조합을 찾는다.
  2) 그 조합으로 '다음 3개월(검증구간)'만 매매한다.
  3) 3개월 뒤, 창을 3개월 앞으로 굴려 다시 1)~2)를 반복한다.
  → 매번 '미래'는 한 번도 안 본 채, 주기적으로 파라미터를 갱신하며 굴린다.

이렇게 이어붙인 '검증구간들의 실제 성적'이 워크포워드 수익률입니다.
실전(주기적 재최적화)과 가장 비슷한, 가장 정직한 백테스트입니다.

추가로 2편 예고대로 '슬리피지'(체결 미끄러짐)도 거래비용에 반영했습니다.
"""
import os
import itertools
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

FEE = 0.001        # 거래 수수료 0.1%
SLIPPAGE = 0.0005  # 슬리피지 0.05% (시장가 체결 시 호가 미끄러짐 — 현실 반영)
IS_DAYS = 365      # 학습(in-sample) 창 길이: 1년
OOS_DAYS = 90      # 검증(out-of-sample) 창 길이: 3개월

def strat_daily_returns(df, short, long):
    """주어진 조합의 '일별' 전략 수익률 시리즈 (수수료+슬리피지 차감)"""
    d = df.copy()
    d["s"] = d["Close"].rolling(short).mean()
    d["l"] = d["Close"].rolling(long).mean()
    d["pos"] = (d["s"] > d["l"]).astype(int).shift(1).fillna(0)  # 다음날 진입(룩어헤드 방지)
    d["ret"] = d["Close"].pct_change().fillna(0)
    d["tr"] = d["pos"].diff().abs().fillna(0)                    # 매매가 일어난 날
    cost = d["tr"] * (FEE + SLIPPAGE)                            # 매매일에만 비용
    return d["pos"] * d["ret"] - cost

def cagr(cum):
    return cum.iloc[-1] ** (365.25 / len(cum)) - 1

def mdd(cum):
    return (cum / cum.cummax() - 1).min()

# ===== 데이터 (가능한 길게) =====
data = yf.download("BTC-USD", period="8y", interval="1d",
                   auto_adjust=True, progress=False)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
data = data.dropna()
print(f"데이터: {data.index[0].date()} ~ {data.index[-1].date()}  ({len(data)}일)")

# ===== 후보 조합의 일별 전략수익률을 전체기간에 대해 미리 계산 =====
shorts = [5, 10, 15, 20, 30, 40]
longs  = [50, 75, 100, 125, 150, 200]
combos = list(itertools.product(shorts, longs))
ret_of = {c: strat_daily_returns(data, c[0], c[1]) for c in combos}

# ===== 워크포워드 루프 =====
wf = pd.Series(0.0, index=data.index)  # 선택된 전략의 일별수익(검증구간만 채움)
picks = []                              # 구간별로 어떤 조합이 뽑혔는지 기록
start = 0
n = len(data)
while start + IS_DAYS + OOS_DAYS <= n:
    is_idx  = data.index[start : start + IS_DAYS]
    oos_idx = data.index[start + IS_DAYS : start + IS_DAYS + OOS_DAYS]
    # 학습구간에서 누적수익이 가장 높은 조합 = 챔피언
    best = max(combos, key=lambda c: (1 + ret_of[c].loc[is_idx]).prod())
    # 그 챔피언으로 '다음 3개월'만 매매
    wf.loc[oos_idx] = ret_of[best].loc[oos_idx]
    picks.append((oos_idx[0], best[0], best[1]))
    start += OOS_DAYS

# ===== 실제 매매한 구간(첫 검증 시작 ~ 마지막 검증 끝)만 평가 =====
first = picks[0][0]
last  = data.index[start - OOS_DAYS + OOS_DAYS - 1] if start <= n else data.index[-1]
wf_ret = wf.loc[first:last]
bh_ret = data["Close"].pct_change().fillna(0).loc[first:last]

wf_cum = (1 + wf_ret).cumprod()
bh_cum = (1 + bh_ret).cumprod()
n_trades = int((wf_ret != wf_ret.shift()).sum())  # 대략적 전환 횟수

print("=" * 54)
print(f"검증 전체구간: {first.date()} ~ {last.date()}  ({len(wf_ret)}일)")
print(f"재최적화 횟수: {len(picks)}회 (3개월마다 파라미터 갱신)")
print("-" * 54)
print(f"{'지표':<14}{'단순보유':>18}{'워크포워드':>18}")
print(f"{'총수익률':<14}{(bh_cum.iloc[-1]-1)*100:>17.1f}%{(wf_cum.iloc[-1]-1)*100:>17.1f}%")
print(f"{'연환산CAGR':<14}{cagr(bh_cum)*100:>17.1f}%{cagr(wf_cum)*100:>17.1f}%")
print(f"{'최대낙폭MDD':<14}{mdd(bh_cum)*100:>17.1f}%{mdd(wf_cum)*100:>17.1f}%")
print("=" * 54)

# 뽑힌 파라미터가 구간마다 얼마나 바뀌는지(안정성) 보기
uniq = {}
for _, s, l in picks:
    uniq[(s, l)] = uniq.get((s, l), 0) + 1
print("구간별로 뽑힌 '최적' 조합 분포 (안정적이라면 한두 개에 쏠려야 함):")
for combo, cnt in sorted(uniq.items(), key=lambda x: -x[1]):
    print(f"  MA {combo[0]:>2}/{combo[1]:<3} : {cnt}회")

# ===== 차트 =====
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(2, 1, figsize=(12, 9), gridspec_kw={"height_ratios": [2, 1]})

ax[0].plot(wf_cum.index, bh_cum, label="Buy & Hold", color="gray")
ax[0].plot(wf_cum.index, wf_cum, label="Walk-forward", color="tab:green")
ax[0].set_title("Walk-forward vs Buy & Hold (cumulative return)")
ax[0].legend(); ax[0].grid(alpha=0.3)

# 시간에 따라 '최적' 단기/장기 MA가 어떻게 출렁이는지
pick_dates = [p[0] for p in picks]
pick_short = [p[1] for p in picks]
pick_long  = [p[2] for p in picks]
ax[1].step(pick_dates, pick_short, where="post", label="chosen short MA", color="tab:blue")
ax[1].step(pick_dates, pick_long,  where="post", label="chosen long MA",  color="tab:red")
ax[1].set_title("Re-optimized 'best' MA per window (unstable = no real edge)")
ax[1].legend(); ax[1].grid(alpha=0.3)

plt.tight_layout()
out = os.path.join(HERE, "walkforward_result.png")
plt.savefig(out, dpi=120)
print("차트 저장:", out)
