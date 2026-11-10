#!/usr/bin/env python3
"""每日更新 data/data.json (只用標準函式庫)。
來源: Yahoo Finance chart API(K線/美股)、Yahoo 股市 TW 頁面(三大法人、河流圖)、證交所/櫃買 openapi(本益比/殖利率/淨值比)。
任何一項抓失敗,就保留 data.json 裡舊的那一項,不會整份壞掉。"""
import json, re, sys, time, datetime as dt, urllib.request
from html.parser import HTMLParser

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept-Language": "zh-TW,zh;q=0.9"}
TZ = dt.timezone(dt.timedelta(hours=8))

def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            print("  retry", i + 1, url[:80], e, file=sys.stderr)
            time.sleep(2 * (i + 1))
    return None

def chart(sym, rng, interval, tw=True):
    t = get("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=%s" % (sym, rng, interval))
    if not t: return None
    try:
        r = json.loads(t)["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        out = []
        for i, ts in enumerate(r["timestamp"]):
            o, h, l, c, v = q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]
            if c is None: continue
            d = dt.datetime.fromtimestamp(ts, TZ if tw else dt.timezone(dt.timedelta(hours=-5))).strftime("%Y-%m-%d")
            f = lambda x: round(x, 2)
            out.append([d, f(o if o is not None else c), f(h if h is not None else c), f(l if l is not None else c), f(c), int((v or 0) / 1000)])
        return out
    except Exception as e:
        print("  parse fail", sym, e, file=sys.stderr); return None

class Tok(HTMLParser):
    def __init__(s): super().__init__(); s.t = []; s.skip = 0
    def handle_starttag(s, tag, a):
        if tag in ("script", "style"): s.skip += 1
    def handle_endtag(s, tag):
        if tag in ("script", "style") and s.skip: s.skip -= 1
    def handle_data(s, d):
        d = d.strip()
        if d and not s.skip: s.t.append(d)

def tokens(url):
    h = get(url)
    if not h: return None
    p = Tok(); p.feed(h); return p.t

def num(x):
    try: return float(x.replace(",", "").replace("+", ""))
    except Exception: return None

def inst(code, mk):
    t = tokens("https://tw.stock.yahoo.com/quote/%s.%s/institutional-trading" % (code, mk))
    if not t: return None
    out = []
    for i, x in enumerate(t):
        if re.fullmatch(r"\d{4}/\d{2}/\d{2}", x):
            v = [num(y) for y in t[i + 1:i + 5]]
            if len(v) == 4 and all(a is not None for a in v):
                out.append([x.replace("/", "-"), int(v[0]), int(v[1]), int(v[2])])
    out = sorted({r[0]: r for r in out}.values())
    return out[-60:] or None

def river(code, mk, kind):
    path = "streamgraph" if kind == "pe" else "pbr-streamgraph"
    t = tokens("https://tw.stock.yahoo.com/quote/%s.%s/%s" % (code, mk, path))
    if not t: return None
    mult = []
    for x in t:
        if re.fullmatch(r"[\d.]+倍", x):
            m = float(x[:-1])
            if m not in mult: mult.append(m)
        if len(mult) == 6: break
    rows = {}
    for i, x in enumerate(t):
        if re.fullmatch(r"\d{4}/\d{2}", x):
            a, b = num(t[i + 1]) if i + 1 < len(t) else None, num(t[i + 2]) if i + 2 < len(t) else None
            if a and b: rows[x.replace("/", "-")] = [x.replace("/", "-"), a, b]
    if len(mult) != 6 or len(rows) < 6: return None
    return {"m": sorted(mult, reverse=True), "r": [rows[k] for k in sorted(rows)][-36:]}

def valuation():
    v = {}
    t = get("https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL")
    if t:
        try:
            for r in json.loads(t):
                v[r["Code"]] = {"pe": num(r.get("PEratio") or ""), "yld": num(r.get("DividendYield") or ""), "pb": num(r.get("PBratio") or "")}
        except Exception as e: print("  twse val fail", e, file=sys.stderr)
    t = get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis")
    if t:
        try:
            for r in json.loads(t):
                v[r["SecuritiesCompanyCode"]] = {"pe": num(r.get("PriceEarningRatio") or ""), "yld": num(r.get("YieldRatio") or ""), "pb": num(r.get("PriceBookRatio") or "")}
        except Exception as e: print("  tpex val fail", e, file=sys.stderr)
    return v

def main():
    try: old = json.load(open("data/data.json", encoding="utf-8"))
    except Exception: old = {"stocks": {}, "us": {}}
    cfg = json.load(open("stocks.json", encoding="utf-8"))
    today = dt.datetime.now(TZ).strftime("%Y-%m-%d")
    val = valuation()
    data = {"updated": dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M"), "order": [[c["code"], c["name"]] for c in cfg], "stocks": {}, "us": {}}
    for c in cfg:
        code, mk = c["code"], c.get("market", "TW")
        sym = "%s.%s" % (code, mk); o = old.get("stocks", {}).get(code, {})
        print("==", sym)
        st = dict(o); st["name"] = c["name"]; st.pop("pc", None)
        d = chart(sym, "2y", "1d")
        if d: st["d"] = d[-260:]
        w = chart(sym, "2y", "1wk")
        if w: st["w"] = [r[:5] for r in w[-60:]]
        m = chart(sym, "5y", "1mo")
        if m: st["m"] = [[r[0][:7]] + r[1:5] for r in m[-60:]]
        i = inst(code, mk)
        if i: st["inst"] = i
        rv = dict(st.get("river") or {})
        for k in ("pe", "pb"):
            r = river(code, mk, k)
            if r: rv[k] = r
        if rv: st["river"] = rv
        if val.get(code) and any(val[code].values()):
            st["val"] = dict(val[code], date=today)
        data["stocks"][code] = st
        time.sleep(1)
    for k, sym in (("DJI", "^DJI"), ("SPX", "^GSPC"), ("IXIC", "^IXIC"), ("SOX", "^SOX")):
        b = chart(sym, "3mo", "1d", tw=False)
        data["us"][k] = {"bars": [r[:5] for r in b[-60:]]} if b else old.get("us", {}).get(k, {"bars": []})
    ok = sum(1 for s in data["stocks"].values() if s.get("d"))
    if ok == 0:
        print("沒有抓到任何股價,保留舊檔", file=sys.stderr); sys.exit(1)
    json.dump(data, open("data/data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("done, stocks with prices:", ok)

if __name__ == "__main__":
    main()
