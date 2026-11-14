"""매일 GitHub Actions에서 실행: tickers.js 종목의 최근 종가와 원/달러 환율을 prices.json에 저장한다.
가격은 Yahoo 차트 데이터를 먼저 쓰고, 실패한 종목만 Stooq로 다시 시도한다. 실패 내역은 로그에 남긴다."""
import csv, io, json, re, time, urllib.request, datetime

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json,text/csv,*/*"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")

def yahoo(t):
    j = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=5d&interval=1d"))
    res = j["chart"]["result"][0]
    ts, closes = res["timestamp"], res["indicators"]["quote"][0]["close"]
    for stamp, c in reversed(list(zip(ts, closes))):
        if c is not None:
            return round(float(c), 4), datetime.datetime.utcfromtimestamp(stamp).strftime("%Y-%m-%d")
    raise ValueError("no close")

def stooq(t):
    text = get(f"https://stooq.com/q/l/?s={t.lower()}.us&f=sd2c&h&e=csv")
    row = next(csv.DictReader(io.StringIO(text)))
    return round(float(row["Close"]), 4), row["Date"]

src = open("tickers.js", encoding="utf-8").read()
tickers = re.findall(r'\["([A-Z\-]+)"', src)

prices, failed = {}, []
for t in tickers:
    got = None
    for fn in (yahoo, stooq):
        try:
            got = fn(t); break
        except Exception as e:
            print(f"{fn.__name__} {t}: {e}")
    if got:
        prices[t] = {"close": got[0], "date": got[1]}
    else:
        failed.append(t)
    time.sleep(0.4)

fx = None
for url in ("https://api.frankfurter.app/latest?from=USD&to=KRW", "https://open.er-api.com/v6/latest/USD"):
    try:
        j = json.loads(get(url)); fx = j["rates"]["KRW"]; break
    except Exception as e:
        print("fx failed", url, e)

old = {}
try:
    old = json.load(open("prices.json", encoding="utf-8"))
except Exception:
    pass

out = {
    "updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
    "usdkrw": fx or old.get("usdkrw"),
    "prices": {**old.get("prices", {}), **prices},
}
json.dump(out, open("prices.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"saved {len(prices)}/{len(tickers)} prices, usdkrw={out['usdkrw']}, failed={failed}")
if not prices:
    raise SystemExit("모든 종목 가격 가져오기 실패")
