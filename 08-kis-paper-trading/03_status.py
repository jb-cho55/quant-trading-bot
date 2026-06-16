"""
계좌 현황 조회 — 잔고 / 보유종목 / 미체결주문  (08단계 보조도구)
──────────────────────────────────────────────────────────────
리밸런싱 전후로 '지금 내 모의계좌가 어떤 상태인가'를 한눈에 본다. 주문은 하지 않는다.
실행: python 03_status.py
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from kis_client import make_kis

kis = make_kis()

bal = kis.account().balance()
krw = bal.deposit("KRW")
print("── 잔고 ──")
print("  예수금  :", f"{int(krw.amount):,} 원" if krw else "조회 없음")
print("  총평가  :", f"{int(bal.amount):,} 원")
print("  매입금액:", f"{int(bal.purchase_amount):,} 원")
print("  평가손익:", f"{int(bal.profit):,} 원 ({float(bal.profit_rate):+.2f}%)")

print("\n── 보유종목 ──")
if not bal.stocks:
    print("  (없음)")
for s in bal.stocks:
    nm = getattr(s, "name", "") or ""
    print(f"  {s.symbol} {nm:<22} {int(s.qty)}주  평가 {int(s.amount):,}원  손익 {float(s.profit_rate):+.2f}%")

print("\n── 미체결 주문 ──")
try:
    pend = kis.account().pending_orders()
    n = len(pend)
    if n == 0:
        print("  (없음)")
    for o in pend.orders:
        nm = getattr(o, "name", "") or ""
        print(f"  {o.symbol} {nm}  {getattr(o,'type','')}  주문 {int(o.qty)}주 / 미체결 {int(o.qty)-int(o.executed_qty)}주  (주문번호 {o.number})")
except Exception as e:
    print("  조회 실패(무시 가능):", type(e).__name__, e)
