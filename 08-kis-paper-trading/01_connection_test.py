"""
KIS 모의투자 연결 스모크 테스트  (08단계 - 플러밍 ③)
──────────────────────────────────────────────────────────────
'연결이 되는가'만 확인하는 최소 스크립트. 주문은 하지 않는다.
  [1] 인증  [2] 모의계좌 예수금/보유종목  [3] KODEX 200 현재가
접속·패치(custtype, throttle)는 kis_client.make_kis() 에 모두 들어있다.

준비: kis_config_example.py → kis_config.py 복사 후 값 채우기.
실행: python 01_connection_test.py
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows cp949 콘솔에서도 한글
except Exception:
    pass

try:
    from kis_client import make_kis
except ModuleNotFoundError as e:
    if "kis_config" in str(e):
        raise SystemExit("[중단] kis_config.py 가 없습니다 — kis_config_example.py 를 복사해 값을 채우세요.")
    raise

print("[1] 인증 (모의투자 모드 + custtype 패치 + throttle)...")
kis = make_kis()
print("    [OK] 인증 객체 생성")

print("\n[2] 모의계좌 잔고 조회...")
bal = kis.account().balance()
krw = bal.deposit("KRW")
print("    예수금(KRW):", f"{int(krw.amount):,} 원" if krw else "조회 결과 없음")
print("    총평가금액 :", f"{int(bal.amount):,} 원")
print("    보유종목   :", len(bal.stocks), "개")
for s in bal.stocks:
    nm = getattr(s, "name", "") or ""
    print(f"      - {s.symbol} {nm}  {int(s.qty)}주  평가 {int(s.amount):,}원  손익 {float(s.profit_rate):+.1f}%")

print("\n[3] 시세 조회 (KODEX 200 = 069500)...")
q = kis.stock("069500").quote()
nm = getattr(q, "name", "") or ""
print(f"    {q.symbol} {nm}  현재가 {int(q.price):,}원")

print("\n[연결 성공] 인증·잔고·시세 모두 정상 — 다음 단계(GTAA 주문 자동화)로 진행 가능.")
