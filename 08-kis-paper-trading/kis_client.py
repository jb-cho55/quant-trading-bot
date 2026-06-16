"""
KIS 모의투자 접속 팩토리 (단일 진실 공급원)  — 08단계
──────────────────────────────────────────────────────────────
이 프로젝트의 모든 스크립트(스모크테스트·GTAA봇)는 여기 make_kis() 로 접속한다.
2026-06-16 디버깅으로 확정한 python-kis(v2.1.6) 두 가지 문제를 여기서 한 번에 처리:

  (1) custtype 누락 → OPSQ0008(호출 후처리 MCI전송 오류)
      python-kis 는 REST 헤더에 custtype 을 넣지 않아, 종목정보(CTPF1604R) 등
      일부 종합도메인 호출이 거부된다. raw 호출에 custtype=P 를 넣으면 정상(rt_cd=0).
      → PyKis.request 를 래핑해 모든 요청에 custtype=P 주입.

  (2) EGW00201(초당 거래건수 초과) 폭주
      라이브러리 기본 종합도메인 한도(19/초)가 이 모의계정엔 너무 높아 한투가
      EGW00201 을 돌려주고, python-kis 가 0.1초 간격 무한재시도로 악화시킨다.
      → 월1회 리밸런싱 봇은 속도가 불필요하므로 종합도메인 한도를 1.2초당 1회로 낮춤.

  (참고) KIS 접근토큰은 '앱키당 1개·발급 1분당 1회' 다. keep_token=True 캐시를
        신뢰하고, 같은 앱키로 토큰을 따로(raw 등) 재발급하지 말 것(기존 토큰 무효화됨).
"""
import kis_config as cfg
from pykis import PyKis
from pykis.utils.rate_limit import RateLimiter
from pykis.logging import setLevel as _kis_set_level

# 레이트리미터 대기/재시도 WARNING 스팸 억제(우리가 의도적으로 throttle 하므로 정상).
# 실제 오류는 예외로 발생하거나 ERROR 로 남으므로 가려지지 않는다.
_kis_set_level("ERROR")

# ── 문제(1) 패치: REST 요청 헤더에 custtype 주입 (모듈 import 시 1회) ──
_orig_request = PyKis.request
def _request_with_custtype(self, path, *, headers=None, **kw):
    headers = dict(headers) if headers else {}
    headers.setdefault("custtype", "P")          # P=개인 / B=법인
    return _orig_request(self, path, headers=headers, **kw)
if getattr(PyKis.request, "__name__", "") != "_request_with_custtype":
    PyKis.request = _request_with_custtype


def make_kis(real_rate_period: float = 1.2):
    """모의투자 PyKis 인스턴스 생성 (custtype 패치 + 종합도메인 throttle 적용)."""
    _required = ("HTS_ID", "REAL_APPKEY", "REAL_SECRETKEY",
                 "VIRTUAL_APPKEY", "VIRTUAL_SECRETKEY", "VIRTUAL_ACCOUNT")
    missing = [k for k in _required if not getattr(cfg, k, "")]
    if missing:
        raise SystemExit("[중단] kis_config.py 에 빈 값: " + ", ".join(missing))

    kis = PyKis(
        id=cfg.HTS_ID,
        account=cfg.VIRTUAL_ACCOUNT,
        appkey=cfg.REAL_APPKEY,                 # 실전(종합) 키 = 시세
        secretkey=cfg.REAL_SECRETKEY,
        virtual_id=cfg.HTS_ID,
        virtual_appkey=cfg.VIRTUAL_APPKEY,      # 모의 키 = 주문/잔고
        virtual_secretkey=cfg.VIRTUAL_SECRETKEY,
        use_websocket=False,
        keep_token=True,                        # 토큰 캐시(1분당 1회 발급 제한 회피)
    )
    # 문제(2) 패치: 호출 한도 완화 (이 모의계정은 KIS 실제 한도가 라이브러리 가정보다
    # 낮아 EGW00201 발생 → 종합/모의 도메인 모두 보수적으로 throttle. 월1회 봇은 속도 불필요)
    kis._rate_limiters["real"] = RateLimiter(1, real_rate_period)
    kis._rate_limiters["virtual"] = RateLimiter(1, 1.1)
    return kis
