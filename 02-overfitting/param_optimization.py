"""
트레이딩 봇 #2 — 파라미터 '과최적화(오버피팅)'의 함정
─────────────────────────────────────────────
1편의 이동평균(20/50)은 그냥 임의로 정한 값이었습니다.
"그럼 가장 수익 좋은 이동평균 조합을 찾으면 되지 않나?"
→ 이 코드는 그 생각이 왜 위험한지를 데이터로 보여줍니다.

방법(워크포워드의 기본 아이디어):
  1) 데이터를 전반부(최적화용, in-sample)와 후반부(검증용, out-of-sample)로 나눈다.
  2) 전반부에서 가장 수익 높은 (단기, 장기) 이동평균 조합을 찾는다.  ← '챔피언'
  3) 그 챔피언 조합을 후반부에 그대로 적용한다.
  4) 보통 후반부 성적은 무너진다 = 과거에 꿰맞췄을 뿐(오버피팅).
"""
import os
import itertools
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

FEE = 0.001

def total_return(df, short, long):
    """주어진 구간에서 (단기/장기 이동평균) 전략의 총수익률을 계산"""
    d = df.copy()
    d["s"] = d["Close"].rolling(short).mean()
    d["l"] = d["Close"].rolling(long).mean()
    d["pos"] = (d["s"] > d["l"]).astype(int).shift(1).fillna(0)  # 다음날 진입
    d["ret"] = d["Close"].pct_change().fillna(0)
    d["tr"] = d["pos"].diff().abs().fillna(0)                    # 거래 발생일
    d["sret"] = d["pos"] * d["ret"] - d["tr"] * FEE             # 수수료 차감
    return (1 + d["sret"]).prod() - 1

# ===== 데이터 (5년, 전·후반 분할) =====
data = yf.download("BTC-USD", period="5y", interval="1d",
                   auto_adjust=True, progress=False)
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)
data = data.dropna()
split = len(data) // 2
IS = data.iloc[:split]    # in-sample  : 최적화에 쓰는 '과거'
OOS = data.iloc[split:]   # out-of-sample : 한 번도 안 본 '미래'
print(f"전반부(최적화용): {IS.index[0].date()} ~ {IS.index[-1].date()}  ({len(IS)}일)")
print(f"후반부(검증용)  : {OOS.index[0].date()} ~ {OOS.index[-1].date()}  ({len(OOS)}일)")

# ===== 전반부에서 모든 조합 백테스트 → 챔피언 찾기 =====
shorts = [5, 10, 15, 20, 30, 40]
longs  = [50, 75, 100, 125, 150, 200]
grid = [(s, l, total_return(IS, s, l)) for s, l in itertools.product(shorts, longs)]
gdf = pd.DataFrame(grid, columns=["short", "long", "is_ret"])
best = gdf.loc[gdf["is_ret"].idxmax()]
bs, bl = int(best["short"]), int(best["long"])

# ===== 챔피언을 '미래'(후반부)에 적용 =====
is_best = best["is_ret"]
oos_best = total_return(OOS, bs, bl)
bh_oos = OOS["Close"].iloc[-1] / OOS["Close"].iloc[0] - 1   # 후반부 단순보유

print("=" * 52)
print(f"전반부 최고 조합(챔피언): MA {bs} / {bl}")
print(f"  전반부(최적화) 수익률    : {is_best*100:+7.1f}%   ← 화려함")
print(f"  후반부(실전 검증) 수익률 : {oos_best*100:+7.1f}%   ← 현실")
print(f"  (참고) 후반부 단순보유   : {bh_oos*100:+7.1f}%")
print("=" * 52)

# ===== 히트맵: 전반부 조합별 수익률 (예뻐 보이는 게 함정) =====
pivot = gdf.pivot(index="short", columns="long", values="is_ret") * 100
fig, ax = plt.subplots(figsize=(9, 6))
im = ax.imshow(pivot, cmap="RdYlGn", aspect="auto")
ax.set_xticks(range(len(pivot.columns))); ax.set_xticklabels(pivot.columns)
ax.set_yticks(range(len(pivot.index)));   ax.set_yticklabels(pivot.index)
ax.set_xlabel("long MA"); ax.set_ylabel("short MA")
ax.set_title("In-sample return (%) by MA combo - looks great, but...")
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        v = pivot.iloc[i, j]
        if pd.notna(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8)
fig.colorbar(im, label="return %")
plt.tight_layout()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overfitting_heatmap.png")
plt.savefig(out, dpi=120)
print("히트맵 저장:", out)
