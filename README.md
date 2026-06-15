# 파이썬 비트코인 트레이딩 봇 — 백테스트 시리즈

파이썬으로 비트코인 트레이딩 전략을 **백테스트**하고, 그 과정에서 배운 것을
블로그로 정리하는 프로젝트입니다. 실거래는 하지 않으며, 모든 코드는 과거 데이터를
이용한 **시뮬레이션**입니다.

> ⚠️ **투자 조언이 아닙니다.** 이 저장소의 모든 코드와 결과는 교육·학습 목적입니다.
> 어떤 종목·전략의 매수·매도 권유도 아니며, 백테스트 결과가 미래 수익을 보장하지
> 않습니다. 투자 판단과 그 결과에 대한 책임은 전적으로 본인에게 있습니다.

## 블로그

전체 설명은 블로그에서 볼 수 있습니다 → **https://cho-jeongbin55.tistory.com**

## 폴더 구조

각 편(post)이 독립 폴더로 나뉘어 있습니다. 폴더 안에 코드·차트·설명(README)이 함께 있습니다.

```
quant-trading-bot/
├── 01-ma-crossover/      #1 이동평균 교차 전략 백테스트
│   ├── btc_ma_backtest.py
│   ├── backtest_result.png
│   └── README.md
├── 02-overfitting/       #2 파라미터 과최적화의 함정
│   ├── param_optimization.py
│   ├── overfitting_heatmap.png
│   └── README.md
├── requirements.txt      공통 의존성
├── LICENSE
└── README.md             (이 파일)
```

## 시리즈 목차

| 편 | 주제 | 코드 | 블로그 |
|---|---|---|---|
| #1 | 이동평균 교차 전략 백테스트 | [`01-ma-crossover/`](01-ma-crossover/) | https://cho-jeongbin55.tistory.com/1 |
| #2 | 파라미터 과최적화(오버피팅)의 함정 | [`02-overfitting/`](02-overfitting/) | (발행 후 링크) |

## 빠른 실행

```bash
pip install -r requirements.txt

# 1편 — 이동평균 교차 백테스트
cd 01-ma-crossover && python btc_ma_backtest.py

# 2편 — 과최적화 시연
cd 02-overfitting && python param_optimization.py
```

Python 3.10+ 권장. 데이터는 [yfinance](https://github.com/ranaroussi/yfinance)로
실시간 다운로드하므로 실행 시점에 따라 숫자가 조금씩 달라질 수 있습니다.

## 라이선스

MIT
