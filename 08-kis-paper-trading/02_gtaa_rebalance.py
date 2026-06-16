"""
GTAA 월간 리밸런싱 — 한투 모의투자  (08단계 ④⑤)
──────────────────────────────────────────────────────────────
전략(07편·KR재검증 합격): 5개 ETF 각각 '종가 > 200일 이동평균'이면 보유(1/5 비중),
아래면 현금. 매월 1회 신호를 보고 목표 비중에 맞춰 사고판다. 분산+추세필터로
낙폭을 줄이는 '마음 편한' 자산배분.

  신호 데이터 : yfinance 일봉(검증과 동일 소스, 무료) — 200일선 계산
  현재가/주문 : KIS 모의투자 (kis_client.make_kis)
  비중 규칙   : 200일선 위 ETF마다 1/5(=20%), 나머지는 현금 (Faber GTAA 관례)
  안전장치    : ① 기본은 DRY-RUN(주문 안 함, 계획만). 실제 주문은 --execute 필요.
              ② 계정 MDD 차단(--max-dd): 총자산이 관측 고점(HWM) 대비 임계%↑ 빠지면
                 신호와 무관하게 전량 현금화. 고점·이력은 gtaa_state.json 에 저장.

실행:
  python 02_gtaa_rebalance.py                    # 계획만 (안전)
  python 02_gtaa_rebalance.py --max-dd 15        # MDD 15% 차단 적용해 계획
  python 02_gtaa_rebalance.py --execute --max-dd 15   # 실제 모의주문 (장중에만 체결)
"""
import sys
import os
import json
import argparse
import math

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import yfinance as yf
import pandas as pd

from kis_client import make_kis

# ── GTAA 대상 5종 (KIS 종목코드 ↔ yfinance 티커 ↔ 이름) ──────────
ETFS = [
    {"code": "069500", "yf": "069500.KS", "name": "KODEX 200 (한국주식)"},
    {"code": "360750", "yf": "360750.KS", "name": "TIGER 미국S&P500 (미국주식)"},
    {"code": "148070", "yf": "148070.KS", "name": "KOSEF 국고채10년 (채권)"},
    {"code": "132030", "yf": "132030.KS", "name": "KODEX 골드선물H (금)"},
    {"code": "329200", "yf": "329200.KS", "name": "TIGER 리츠부동산인프라 (부동산)"},
]
N = len(ETFS)
MA_WINDOW = 200

# 거래비용 추정(보고서 4층 모델 간이판). 국내 상장 ETF는 매도 증권거래세 면제.
COMMISSION = 0.00015   # 수수료 추정 0.015%/편도
SLIPPAGE = 0.0010      # 반스프레드+시장충격 추정 0.1%/편도 (보수적)

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtaa_state.json")


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"hwm": None, "last_run": None, "history": []}


def save_state(hwm, run_date, history):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"hwm": round(hwm), "last_run": run_date, "history": history},
                  f, ensure_ascii=False, indent=2)


def fetch_signal():
    """yfinance 일봉으로 각 ETF의 '종가>200일선' 여부와 최신 종가/날짜 반환."""
    sig = {}
    for e in ETFS:
        data = yf.download(e["yf"], period="1y", interval="1d",
                           auto_adjust=True, progress=False)
        s = data["Close"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        s = s.dropna()
        if len(s) < MA_WINDOW:
            raise SystemExit(f"[중단] {e['yf']} 일봉이 {len(s)}개뿐 — 200일선 계산 불가.")
        ma = s.rolling(MA_WINDOW).mean().iloc[-1]
        last = s.iloc[-1]
        sig[e["code"]] = {
            "above": bool(last > ma),
            "last": float(last),
            "ma": float(ma),
            "date": str(s.index[-1].date()),
        }
    return sig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="실제 모의주문 실행(기본은 계획만)")
    ap.add_argument("--max-dd", type=float, default=0.0,
                    help="계정 MDD 차단 임계%(예: 15). 0이면 미사용. 관측 고점 대비 이만큼 빠지면 전량 현금화")
    args = ap.parse_args()
    mode = "실제 주문(EXECUTE)" if args.execute else "DRY-RUN(계획만, 주문 안 함)"
    print(f"=== GTAA 리밸런싱 — {mode} ===\n")

    # 1) 신호
    print("[1] 신호 계산 (yfinance 200일선)")
    sig = fetch_signal()
    for e in ETFS:
        s = sig[e["code"]]
        mark = "보유" if s["above"] else "현금"
        print(f"    {e['code']} {e['name']:<26} 종가 {s['last']:>10,.0f} / MA200 {s['ma']:>10,.0f}  → {mark}  ({s['date']})")
    held = [e for e in ETFS if sig[e["code"]]["above"]]
    print(f"    → 보유 대상 {len(held)}/{N}종, 현금비중 {(N-len(held))/N*100:.0f}%")
    run_date = sig[ETFS[0]["code"]]["date"]

    # 2) KIS 잔고 + 현재가
    print("\n[2] 모의계좌 잔고 + 현재가")
    kis = make_kis()
    bal = kis.account().balance()
    krw = bal.deposit("KRW")
    cash = float(krw.amount) if krw else 0.0
    holdings = {s.symbol: int(s.qty) for s in bal.stocks}
    print("    (시세 5종 조회 중 — 호출제한 throttle 로 ~10초 소요)")
    prices = {}
    for e in ETFS:
        q = kis.stock(e["code"]).quote()
        prices[e["code"]] = int(q.price)
    held_value = sum(holdings.get(e["code"], 0) * prices[e["code"]] for e in ETFS)
    total = cash + held_value
    print(f"    예수금 {cash:,.0f}원 + 보유평가 {held_value:,.0f}원 = 총자산 {total:,.0f}원")
    if holdings:
        for code, qty in holdings.items():
            print(f"      보유: {code}  {qty}주")

    # 2.5) 상태 로드 → 고점(HWM)/드로다운 갱신 → MDD 차단 판정
    state = load_state()
    hwm = max(float(state.get("hwm") or total), total)
    dd = total / hwm - 1.0 if hwm > 0 else 0.0
    force_cash = bool(args.max_dd and args.max_dd > 0 and dd <= -args.max_dd / 100.0)
    line = f"    고점(HWM) {hwm:,.0f}원 / 현재 드로다운 {dd*100:+.1f}%"
    if args.max_dd and args.max_dd > 0:
        line += f" / 차단임계 -{args.max_dd:.0f}%"
        if force_cash:
            line += "  → ★MDD 차단 발동: 신호 무시하고 전량 현금화"
    else:
        line += "  (차단 미설정 — --max-dd 로 켜기)"
    print(line)

    # 상태 저장(관측 기준; dry-run/execute 모두 기록, 같은 날짜는 갱신)
    entry = {"date": run_date, "mode": "execute" if args.execute else "dry-run",
             "total": round(total), "hwm": round(hwm), "dd": round(dd, 4),
             "signal_held": [e["code"] for e in held], "forced_cash": force_cash}
    history = state.get("history", [])
    if history and history[-1].get("date") == run_date:
        history[-1] = entry
    else:
        history.append(entry)
    save_state(hwm, run_date, history)

    # 3) 목표 수량 → 주문 산출
    print("\n[3] 목표 비중 → 주문 계획" + ("  (MDD 차단 → 전량 현금 목표)" if force_cash else ""))
    print(f"    {'종목':<26}{'신호':>5}{'현재':>7}{'목표':>7}{'주문':>10}{'예상금액':>14}")
    print("    " + "-" * 70)
    orders = []  # (code, name, side, qty, price)
    weight = 1.0 / N
    for e in ETFS:
        code, price = e["code"], prices[e["code"]]
        cur_qty = holdings.get(code, 0)
        if force_cash or not sig[code]["above"]:
            tgt_qty = 0
        else:
            tgt_qty = math.floor(total * weight / price)
        delta = tgt_qty - cur_qty
        side = "-" if delta == 0 else ("매수" if delta > 0 else "매도")
        amt = abs(delta) * price
        mark = "현금" if force_cash else ("보유" if sig[code]["above"] else "현금")
        order_str = "-" if delta == 0 else f"{side} {abs(delta)}주"
        print(f"    {e['name']:<26}{mark:>5}{cur_qty:>7}{tgt_qty:>7}{order_str:>10}{amt:>13,.0f}원")
        if delta != 0:
            orders.append((code, e["name"], "buy" if delta > 0 else "sell", abs(delta), price))

    if not orders:
        print("\n    리밸런싱 불필요 — 이미 목표 비중. 끝.")
        return

    # 비용 추정
    gross = sum(q * p for _, _, _, q, p in orders)
    est_cost = gross * (COMMISSION + SLIPPAGE)
    print(f"\n    거래대금 합계 {gross:,.0f}원 / 추정비용 {est_cost:,.0f}원"
          f" (수수료 {COMMISSION*100:.3f}%+슬리피지 {SLIPPAGE*100:.1f}%/편도, 국내ETF 매도세 면제)")

    # 4) 실행
    if not args.execute:
        print("\n[DRY-RUN] 위 계획대로 주문하려면:  python 02_gtaa_rebalance.py --execute")
        print("          (모의투자라도 실제 체결은 장중 09:00~15:30 에만 이뤄집니다)")
        return

    print("\n[4] 주문 실행 (매도 먼저 → 매수)")
    for code, name, side, qty, price in sorted(orders, key=lambda o: o[2]):  # 'buy'<'sell' → sell first
        try:
            stock = kis.stock(code)
            order = stock.sell(price=None, qty=qty) if side == "sell" else stock.buy(price=None, qty=qty)
            num = getattr(order, "order_number", None) or getattr(order, "number", None) or "?"
            print(f"    OK   {side} {name} {qty}주  (주문번호 {num})")
        except Exception as ex:
            print(f"    FAIL {side} {name} {qty}주  {type(ex).__name__}: {ex}")
    print("\n[완료] 체결 결과는 잠시 후 잔고로 확인하세요 (시장가는 즉시 체결되는 편).")


if __name__ == "__main__":
    main()
