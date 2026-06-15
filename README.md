# 파이썬 비트코인 트레이딩 봇 — 백테스트 시리즈

파이썬으로 비트코인 트레이딩 전략을 **백테스트**하고, 그 과정에서 배운 것을
블로그로 정리하는 프로젝트입니다. 실거래는 하지 않으며, 모든 코드는 과거 데이터를
이용한 **시뮬레이션**입니다.

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

## 한눈에 보는 결론

1~3편: **단순 이동평균으로 "총수익"에서 단순 보유를 이기긴 어렵다.**
4~5편: 목표를 **"덜 잃기(위험조정수익)"** 로 바꾸자, 두 전략이 워크포워드 검증을 통과했다.

| 검증 통과 전략 | Sharpe | MDD | 비고 |
|---|---|---|---|
| 추세필터(>MA200) | 0.89 | −54.5% | 단순·견고, 후보 1순위 |
| 변동성 돌파 | 0.92 | −49% | 낙폭 방어 최강, 단 체결비용 민감 |
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
```

Python 3.10+ 권장. 데이터는 [yfinance](https://github.com/ranaroussi/yfinance)로
실시간 다운로드하므로 실행 시점에 따라 숫자가 조금씩 달라질 수 있습니다.

## 라이선스

MIT
