"""
KIS Open API 접속 설정 템플릿  (08단계 - 한투 모의투자 연결)
──────────────────────────────────────────────────────────────
사용법:
  1) 이 파일을 같은 폴더에 kis_config.py 라는 이름으로 복사한다.
  2) 아래 빈 문자열을 본인 값으로 채운다.
     (kis_config.py 는 .gitignore 로 제외되므로 GitHub에 안 올라감 = 비밀키 안전)
  3) python 01_connection_test.py 로 연결을 확인한다.

값 발급처: KIS Developers  https://apiportal.koreainvestment.com
  ※ 서비스 신청 시 [종합계좌]+[모의계좌] 둘 다 체크하면 키가 각각 발급된다.
  ※ 모의투자라도 '실전(종합계좌) 키'가 필요하다 — KIS 모의 도메인은 시세 일부를
     제공하지 않아, 시세는 실전 키로, 주문/잔고는 모의 키로 처리하기 때문.
"""

HTS_ID = ""                       # 한국투자증권 HTS/MTS 로그인 아이디

# ── 실전(종합계좌) 키 : '시세 조회'에만 사용 (이 봇은 실전 주문은 하지 않음) ──
REAL_APPKEY    = ""               # 종합계좌 APP Key
REAL_SECRETKEY = ""               # 종합계좌 APP Secret

# ── 모의(모의계좌) 키 : '모의 주문·잔고'에 사용 ──
VIRTUAL_APPKEY    = ""            # 모의계좌 APP Key
VIRTUAL_SECRETKEY = ""            # 모의계좌 APP Secret
VIRTUAL_ACCOUNT   = ""            # 모의계좌번호. 예: "50123456-01"  (뒤 -01 은 상품코드)
