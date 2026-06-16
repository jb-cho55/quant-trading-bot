# #8 — 백테스트를 끝낸 전략, 증권사에 연결하다 (한투 모의투자)

1~7편은 전부 **과거 데이터 시뮬레이션**이었다. 8편에서 드디어 검증을 마친
**GTAA 자산배분**을 한국투자증권 **KIS Open API 모의투자**(실제 돈 0원)에 연결한다.
백테스트와 실거래 사이의 진짜 강을 건너는 편 — 그리고 그 과정에서 만난 버그까지.

> ⚠️ **모의투자(가상자금)입니다.** 실제 주문·실제 돈이 아니며 투자 권유가 아닙니다.

## 전략 (07편을 한국 ETF로)

[#7 GTAA](../07-asset-allocation/)를 한국 상장 ETF 5종으로 옮겨 동일 메커니즘 재검증(합격):

| 자산군 | ETF | 코드 |
|---|---|---|
| 한국주식 | KODEX 200 | 069500 |
| 미국주식 | TIGER 미국S&P500 | 360750 |
| 채권 | KOSEF 국고채10년 | 148070 |
| 금 | KODEX 골드선물(H) | 132030 |
| 부동산 | TIGER 리츠부동산인프라 | 329200 |

각 ETF가 **200일선 위면 보유(1/5 비중), 아래면 현금**. 매월 1회 리밸런싱.

## 파일

| 파일 | 내용 |
|---|---|
| `kis_client.py` | 접속 팩토리(단일 진실 공급원) — python-kis 패치 캡슐화 |
| `kis_config_example.py` | 키 설정 템플릿 (→ `kis_config.py`로 복사, 비밀키는 **gitignore**) |
| `01_connection_test.py` | 연결 스모크 테스트(인증·잔고·시세) |
| `02_gtaa_rebalance.py` | **GTAA 월간 리밸런싱** — dry-run 기본, `--execute`, `--max-dd` |
| `03_status.py` | 계좌 현황(잔고·보유·미체결) 조회 |
| `kr_gtaa_validation.py` | 한국 ETF GTAA 사전 재검증 + 차트 |

## 셋업 (모의계좌 + 키)

1. 한투 홈페이지 → **모의투자 신청**(모의계좌번호 발급)
2. **KIS Developers**에서 서비스 신청 시 **[종합계좌]+[모의계좌] 둘 다 체크**
   → APP Key/Secret이 **두 쌍** 발급 (모의투자라도 시세는 실전 키로 받기 때문)
3. `kis_config_example.py` → `kis_config.py`로 복사 후 값 6개 채우기
4. `python 01_connection_test.py` → `[연결 성공]` 확인

## 실행

```bash
python 02_gtaa_rebalance.py                  # 이번 달 계획만 출력(안전, 주문 안 함)
python 02_gtaa_rebalance.py --max-dd 15      # 계정 MDD 15% 차단 적용
python 02_gtaa_rebalance.py --execute --max-dd 15   # 실제 모의주문(장중 09:00~15:30)
```

**안전장치:** ① 기본은 dry-run(계획만), 실주문은 `--execute` 필요.
② `--max-dd N`: 총자산이 관측 고점 대비 N% 넘게 빠지면 신호 무시하고 전량 현금화
(고점·이력은 `gtaa_state.json`에 저장).

## 만난 버그 — python-kis(v2.1.6) 시세/주문이 `OPSQ0008`로 거부

연결 디버깅에서 라이브러리 결함 2개를 찾아 `kis_client.py`에서 우회했다:

1. **custtype 누락 → `OPSQ0008`(MCI전송 오류):** python-kis가 REST 헤더에
   `custtype`을 넣지 않아 종목정보 조회 등 일부 호출이 거부됨. raw 호출에
   `custtype=P`를 넣으면 정상(rt_cd=0)임을 A/B로 확인 → `PyKis.request`를 래핑해 주입.
2. **`EGW00201`(초당 한도) 폭주:** 기본 한도(19/초)가 이 모의계정엔 과해
   한투가 거부 → 종합/모의 도메인 호출을 보수적으로 throttle(월 1회 봇은 속도 불필요).

> KIS 접근토큰은 **앱키당 1개·발급 1분당 1회**(새로 발급하면 기존 토큰 무효화).
> `keep_token` 캐시를 신뢰하고 토큰을 따로 재발급하지 말 것.

*숫자는 실행 시점 시세에 따라 달라진다. 모의투자 자체가 진짜 전진(forward) 테스트다.*
