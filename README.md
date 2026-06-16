# 파이썬 트레이딩 봇 — 백테스트에서 모의투자까지

파이썬으로 트레이딩 전략을 **백테스트**하고, 검증을 통과한 전략을 실제 증권사
**모의투자(실제 돈 0원)**까지 연결하며, 그 과정에서 배운 것을 블로그로 정리하는
프로젝트입니다. 비트코인 이동평균 백테스트(#1)에서 시작해, 주식·자산배분을 거쳐
한국투자증권 API 모의투자(#8)로 확장했습니다.

> ⚠️ **투자 조언이 아닙니다.** 이 저장소의 모든 코드와 결과는 교육·학습 목적입니다.
> 어떤 종목·전략의 매수·매도 권유도 아니며, 백테스트 결과가 미래 수익을 보장하지
> 않습니다. 투자 판단과 그 결과에 대한 책임은 전적으로 본인에게 있습니다.

## 블로그

전체 설명은 블로그에서 볼 수 있습니다 → **https://cho-jeongbin55.tistory.com**

## 시리즈 목차

| 편 | 주제 | 코드 | 블로그 |
|---|---|---|---|
| #1 | 이동평균 교차 전략 백테스트 | [`01-ma-crossover/`](01-ma-crossover/) | https://cho-jeongbin55.tistory.com/1 |
| #2 | 파라미터 과최적화(오버피팅)의 함정 | [`02-overfitting/`](02-overfitting/) | https://cho-jeongbin55.tistory.com/2 |
| #3 | 워크포워드 분석: 가장 정직한 백테스트 | [`03-walkforward/`](03-walkforward/) | https://cho-jeongbin55.tistory.com/3 |
| #4 | 전략 토너먼트: '덜 잃는' 전략 찾기 | [`04-strategy-tournament/`](04-strategy-tournament/) | (발행 예정) |
| #5 | 변동성 돌파: 유명세 vs 현실 | [`05-volatility-breakout/`](05-volatility-breakout/) | (발행 예정) |
| #6 | 성장주에 옮겨 심기: 전략은 종목을 탄다 | [`06-growth-stocks/`](06-growth-stocks/) | (작성 예정) |
| #7 | 자산배분(GTAA): '덜 잃기'의 정석 | [`07-asset-allocation/`](07-asset-allocation/) | (작성 예정) |
| #8 | 한투 모의투자 연결: 백테스트→실전 | [`08-kis-paper-trading/`](08-kis-paper-trading/) | (작성 예정) |

## 한눈에 보는 결론

- **#1~3:** 단순 이동평균으로 "총수익"에서 단순 보유를 이기긴 어렵다.
- **#4~5:** 목표를 **"덜 잃기(위험조정수익)"** 로 바꾸자, 추세필터·변동성 돌파가 워크포워드를 통과.
- **#6~7:** 한 자산의 전략은 다른 자산에서 무너진다 → **분산(자산배분)이 가장 큰 무료 점심.** GTAA로 낙폭을 절반으로.
- **#8:** 검증한 GTAA를 한투 모의투자에 연결. 백테스트와 실거래 사이의 강(API·체결·비용·버그)을 건넌다.

| 검증 통과 전략 | Sharpe | MDD | 비고 |
|---|---|---|---|
| 추세필터(>MA200) | 0.89 | −54.5% | 단순·견고, 후보 1순위 |
| 변동성 돌파 | 0.92 | −49% | 낙폭 방어 최강, 단 체결비용 민감 |
| GTAA 자산배분 | 0.69 | −23% | 낙폭 최소, 마음 편한 운용 |
| (벤치마크) 단순 보유 | 0.84 | −76.6% | — |

📁 공개 전략 조사·검증 상태는 [`STRATEGY-CATALOG.md`](STRATEGY-CATALOG.md) 참고.

## 폴더 구조

```
quant-trading-bot/
├── 01-ma-crossover/        #1 이동평균 교차 백테스트
├── 02-overfitting/         #2 과최적화의 함정
├── 03-walkforward/         #3 워크포워드 분석
├── 04-strategy-tournament/ #4 전략 토너먼트 + 추세필터 검증
├── 05-volatility-breakout/ #5 변동성 돌파 검증
├── 06-growth-stocks/       #6 성장주 전략 검증(전이 실패→분산)
├── 07-asset-allocation/    #7 GTAA 자산배분
├── 08-kis-paper-trading/   #8 한투 모의투자 연결(GTAA 자동 리밸런싱)
├── STRATEGY-CATALOG.md     공개 전략 카탈로그
├── requirements.txt        공통 의존성
├── LICENSE
└── README.md
```

## 빠른 실행

```bash
pip install -r requirements.txt

cd 01-ma-crossover        && python btc_ma_backtest.py
cd 02-overfitting         && python param_optimization.py
cd 03-walkforward         && python walkforward_backtest.py
cd 04-strategy-tournament && python strategy_comparison.py
cd 05-volatility-breakout && python volatility_breakout.py
cd 07-asset-allocation    && python gtaa_timing.py
```

\#8 모의투자는 본인 KIS API 키가 필요합니다 — [`08-kis-paper-trading/`](08-kis-paper-trading/) README 참고.

Python 3.10+ 권장. 데이터는 [yfinance](https://github.com/ranaroussi/yfinance)로
실시간 다운로드하므로 실행 시점에 따라 숫자가 조금씩 달라질 수 있습니다.

## 라이선스

MIT
