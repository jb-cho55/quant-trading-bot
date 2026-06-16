"""
KR ETF 버전 GTAA 재검증 — 한투 모의투자 연결 전 사전 검증 (08단계)
─────────────────────────────────────────────────────────────
배경: 07편에서 GTAA(각 자산 200일선 위면 보유/아래면 현금, 월간 리밸런싱)가
      US ETF 5종(SPY/EFA/IEF/GLD/VNQ)으로 위험조정수익 우위를 보였다(20년).
      한투 '국내' 모의투자에 연결하려면 같은 메커니즘을 '한국 상장 ETF'로 옮겨야 한다.
      → 자산만 바꿔도 GTAA 효과(낙폭↓, Sharpe 단순보유 이상)가 유지되는지 재검증.

자산 매핑 (Faber 5자산군 → 한국 상장 ETF, yfinance .KS):
      한국주식 KODEX 200 / 미국주식 TIGER 미국S&P500 / 채권 KOSEF 국고채10년
      / 금 KODEX 골드선물(H) / 부동산 TIGER 리츠부동산인프라
정직한 한계: 한국 ETF는 상장 역사가 짧아(상당수 2019~2020) 검증 윈도우가 US판(20년)보다
      훨씬 짧다. 데이터 가용성은 코드가 다운로드해서 실제로 확인하고 윈도우를 출력한다.
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows cp949 콘솔에서도 한글/기호 출력
except Exception:
    pass
plt.rcParams["font.family"] = "Malgun Gothic"  # 차트 한글 (Windows 기본 폰트)
plt.rcParams["axes.unicode_minus"] = False

COST = 0.0015  # 회전율 1단위당 비용(US판과 동일 가정. 국내 ETF는 거래세 면제라 보수적인 편)

# Faber 5자산군을 한국 상장 ETF로 매핑. 데이터 가용성은 개별 다운로드로 확인.
CANDIDATES = {
    "069500.KS": "KODEX 200 (한국주식)",
    "360750.KS": "TIGER 미국S&P500 (미국주식)",
    "148070.KS": "KOSEF 국고채10년 (채권)",
    "132030.KS": "KODEX 골드선물H (금)",
    "329200.KS": "TIGER 리츠부동산인프라 (부동산)",
}
BENCH_TICKER = "069500.KS"   # '주식 100%' 벤치마크 = KODEX 200


def fetch(tkr):
    """단일 ETF 종가 다운로드. yfinance 버전별 반환형(Series/DataFrame) 모두 처리."""
    data = yf.download(tkr, period="max", interval="1d",
                       auto_adjust=True, progress=False)
    if data is None or len(data) == 0:
        return None
    s = data["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.dropna()


# ── 개별 다운로드 + 가용성 점검 ───────────────────────────────
print("데이터 가용성 점검:")
series_px, names = {}, {}
for tkr, name in CANDIDATES.items():
    try:
        s = fetch(tkr)
        if s is not None and len(s) >= 250:
            series_px[tkr] = s
            names[tkr] = name
            print(f"  OK   {tkr:<11}{name:<26}{s.index[0].date()} ~ {s.index[-1].date()}  ({len(s)}일)")
        else:
            got = 0 if s is None else len(s)
            print(f"  SKIP {tkr:<11}{name:<26}데이터 부족 또는 없음({got}일)")
    except Exception as e:
        print(f"  FAIL {tkr:<11}{name:<26}{type(e).__name__}: {e}")

if len(series_px) < 2:
    raise SystemExit("\n사용 가능한 ETF가 2개 미만 — 티커/네트워크 확인 필요. 중단.")

# 공통 구간으로 정렬 (가장 늦게 상장한 ETF가 윈도우를 제한)
px = pd.concat(series_px, axis=1).dropna()
px.columns = list(series_px.keys())
ASSETS = list(px.columns)
aret = px.pct_change().fillna(0)

# ── GTAA 로직 (07편과 동일) ──────────────────────────────────
above = (px > px.rolling(200).mean()).astype(float)        # 200일선 위/아래
monthly_sig = above.resample("ME").last()                  # 월말 신호
pos = monthly_sig.shift(1).reindex(px.index, method="ffill").fillna(0)  # 다음 달 보유
weight = pos / len(ASSETS)                                 # 켜진 자산에 1/N (현금슬롯 0)
strat_ret = (weight.shift(1) * aret).sum(axis=1)
turnover = (weight - weight.shift(1)).abs().sum(axis=1).fillna(0)
strat_ret = strat_ret - turnover * COST

# 벤치마크
ew_ret = aret.mean(axis=1)                                 # 동일가중 단순보유
bench_ret = aret[BENCH_TICKER] if BENCH_TICKER in ASSETS else None

# ── 성과 지표 ────────────────────────────────────────────────
start = px.index[210]                                      # 200일 MA 워밍업 이후
years_total = (px.index[-1] - start).days / 365.25


def metrics(r):
    r = r.loc[start:].dropna()
    cum = (1 + r).cumprod()
    years = (r.index[-1] - r.index[0]).days / 365.25
    ann = len(r) / years
    cagr = cum.iloc[-1] ** (1 / years) - 1
    mdd = (cum / cum.cummax() - 1).min()
    sh = (r.mean() / r.std()) * np.sqrt(ann) if r.std() > 0 else 0
    return cum, cagr, mdd, sh


series = {"GTAA timing (KR ETF)": strat_ret, "동일가중 단순보유": ew_ret}
if bench_ret is not None:
    series[f"{names[BENCH_TICKER].split('(')[0].strip()} 100%"] = bench_ret

print(f"\n검증 윈도우: {start.date()} ~ {px.index[-1].date()}  (약 {years_total:.1f}년)")
print(f"자산: {', '.join(names[t] for t in ASSETS)}")
if years_total < 5:
    print("[주의] 윈도우가 5년 미만 - 표본이 얇으니 결과는 '신호' 수준으로만 해석할 것.")
print(f"\n{'전략':<24}{'총수익':>10}{'CAGR':>8}{'MDD':>8}{'Sharpe':>9}")
print("-" * 59)
cums = {}
for name, r in series.items():
    cum, cagr, mdd, sh = metrics(r)
    cums[name] = cum
    print(f"{name:<24}{(cum.iloc[-1]-1)*100:>9.0f}%{cagr*100:>7.0f}%{mdd*100:>7.0f}%{sh:>9.2f}")

print("\n* 합격 기준: 동일가중 단순보유 대비 MDD를 줄이면서 Sharpe가 떨어지지 않으면 통과.")
print("  (07편 US판처럼 '비슷하게 벌고 덜 잃는다'가 KR ETF에서도 성립하는지 확인)")

# ── 차트 ────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
fig, ax = plt.subplots(figsize=(12, 7))
for name, cum in cums.items():
    lw = 2.2 if name.startswith("GTAA") else 1.3
    ax.plot(cum.index, cum, label=name, lw=lw)
ax.set_yscale("log")
ax.set_title("GTAA multi-asset timing — KR-listed ETFs (log scale)")
ax.legend(); ax.grid(alpha=0.3, which="both")
plt.tight_layout()
out = os.path.join(HERE, "gtaa_kr_validation.png")
plt.savefig(out, dpi=120)
print("\n차트 저장:", out)
