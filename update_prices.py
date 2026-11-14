"""매일 GitHub Actions에서 실행: tickers.js의 종목 전날 종가와 원/달러 환율을 prices.json에 저장한다."""
import csv, io, json, re, urllib.request, datetime

UA = {"User-Agent": "Mozilla/5.0 (tax-calc price updater)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")

src = open("tickers.js", encoding="utf-8").read()
tickers = re.findall(r'\["([A-Z\-]+)"', src)

prices = {}
for i in range(0, len(tickers), 20):
    chunk = tickers[i:i + 20]
    syms = "+".join(t.lower() + ".us" for t in chunk)
    try:
        text = get(f"https://stooq.com/q/l/?s={syms}&f=sd2c&h&e=csv")
        for row in csv.DictReader(io.StringIO(text)):
            sym = (row.get("Symbol") or "").upper().replace(".US", "")
            close = row.get("Close")
            try:
                prices[sym] = {"close": round(float(close), 4), "date": row.get("Date")}
            except (TypeError, ValueError):
                pass
    except Exception as e:
        print("price chunk failed", chunk, e)

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
    "updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
    "usdkrw": fx or old.get("usdkrw"),
    "prices": {**old.get("prices", {}), **prices},
}
json.dump(out, open("prices.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"saved {len(prices)} prices, usdkrw={out['usdkrw']}")
