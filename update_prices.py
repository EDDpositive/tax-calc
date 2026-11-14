"""매일 GitHub Actions에서 실행: tickers.js의 종목 전날 종가와 원/달러 환율을 prices.json에 저장한다.

가격 소스: stooq CSV를 먼저 시도하고, 못 받은 종목은 Yahoo Finance chart API로 채운다.
(stooq의 /q/l/ CSV 엔드포인트가 404로 폐기되어 2차 소스를 둔다.)
"""
import csv, io, json, re, urllib.request, datetime

UA = {"User-Agent": "Mozilla/5.0 (tax-calc price updater)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")

src = open("tickers.js", encoding="utf-8").read()
tickers = re.findall(r'\["([A-Z\-]+)"', src)

prices = {}

def stooq(syms):
    syms_q = "+".join(s.lower() + ".us" for s in syms)
    text = get(f"https://stooq.com/q/l/?s={syms_q}&f=sd2c&h&e=csv")
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        sym = (row.get("Symbol") or "").upper().replace(".US", "")
        close = row.get("Close")
        try:
            out[sym] = {"close": round(float(close), 4), "date": row.get("Date")}
        except (TypeError, ValueError):
            pass
    return out

def yahoo(sym):
    text = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d")
    res = json.loads(text)["chart"]["result"][0]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    if not closes:
        return None
    date = datetime.datetime.fromtimestamp(res["timestamp"][-1], datetime.timezone.utc).strftime("%Y-%m-%d")
    return {"close": round(closes[-1], 4), "date": date}

for i in range(0, len(tickers), 20):
    chunk = tickers[i:i + 20]
    try:
        prices.update(stooq(chunk))
    except Exception as e:
        print("stooq chunk failed", chunk, e)

missing = [t for t in tickers if t not in prices]
for t in missing:
    try:
        p = yahoo(t)
        if p:
            prices[t] = p
    except Exception as e:
        print("yahoo failed", t, e)

fx = None
try:
    fx = json.loads(get("https://api.frankfurter.app/latest?from=USD&to=KRW"))["rates"]["KRW"]
except Exception as e:
    print("fx failed", e)

old = {}
try:
    old = json.load(open("prices.json", encoding="utf-8"))
except Exception:
    pass

out = {
    "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "usdkrw": fx or old.get("usdkrw"),
    "prices": {**old.get("prices", {}), **prices},
}
json.dump(out, open("prices.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"saved {len(prices)} prices ({len(missing)} via yahoo fallback), usdkrw={out['usdkrw']}")
