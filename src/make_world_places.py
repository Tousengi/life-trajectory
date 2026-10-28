"""从 Natural Earth 的全球城市点生成 src/world_places.json（中国、日本以外的城市）。

数据（公有领域）：https://github.com/nvkelso/natural-earth-vector 的
  geojson/ne_10m_populated_places.geojson、geojson/ne_110m_admin_0_countries.geojson
用法：python3 -I src/make_world_places.py places.geojson countries110.geojson

输出 {"places": [...], "extra": {...}}：
  places：每条 [中文名, 英文名, 国家（和页面里的中文写法一致）, 纬度, 经度, 州/省（英文）, 日文名, 繁体名, 人口]
  extra：页面里已有的城市 → [州/省, 日文名, 繁体名, 人口]，补给它们，好让按州名、日文名也能搜到
  countries：国家中文名 → 英文名，好让用英文国名也能搜
中国、日本、台湾、香港、澳门不收，用页面里人工核对过的那份；和已有城市重复的只补信息不重复收。
"""
import json
import math
import re
import sys
from pathlib import Path

SKIP = {"CHN", "JPN", "TWN", "HKG", "MAC"}
# 数据里没有中文名的小国家
COUNTRY_ZH = {
    "Andorra": "安道尔", "Antigua and Barbuda": "安提瓜和巴布达", "Aruba": "阿鲁巴", "Bahrain": "巴林", "Barbados": "巴巴多斯",
    "Cape Verde": "佛得角", "Comoros": "科摩罗", "Curacao": "库拉索", "Dominica": "多米尼克",
    "Federated States of Micronesia": "密克罗尼西亚", "French Polynesia": "法属波利尼西亚", "Grenada": "格林纳达",
    "Kiribati": "基里巴斯", "Liechtenstein": "列支敦士登", "Malta": "马耳他", "Marshall Islands": "马绍尔群岛", "Monaco": "摩纳哥",
    "Palau": "帕劳", "Saint Kitts and Nevis": "圣基茨和尼维斯", "Saint Lucia": "圣卢西亚",
    "Saint Vincent and the Grenadines": "圣文森特和格林纳丁斯", "Samoa": "萨摩亚", "San Marino": "圣马力诺",
    "Sao Tome and Principe": "圣多美和普林西比", "Seychelles": "塞舌尔", "South Sudan": "南苏丹",
    "Svalbard and Jan Mayen Islands": "斯瓦尔巴", "Tonga": "汤加", "Tuvalu": "图瓦卢", "Vatican": "梵蒂冈",
}
root = Path(__file__).parent
page = (root / "page.html").read_text()


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    return 6371 * math.acos(min(1, math.sin(la1) * math.sin(la2) + math.cos(la1) * math.cos(la2) * math.cos(lo1 - lo2)))


# 页面里的国家写法：中文 → 各种别名
block = re.search(r"const COUNTRY_ALIASES = \{(.*?)\n\};", page, re.S).group(1)
canon = {}
for zh, al in re.findall(r'([^\s,{]+): "([^"]*)"', block):
    for n in [zh, *al.split("|")]:
        canon[n.lower()] = zh

existing = [(r[0], float(r[3]), float(r[4]), r[2])
            for r in re.findall(r'^([^|\n`]+)\|([^|\n]+)\|([^|\n]+)\|(-?[\d.]+)\|(-?[\d.]+)$', page, re.M)]


def main(places_path, countries_path):
    zh_country = {}
    for f in json.load(open(countries_path))["features"]:
        p = f["properties"]
        zh_country[p["ADM0_A3"]] = p.get("NAME_ZH") or p["NAME"]
    out, extra, countries = [], {}, {}
    for f in json.load(open(places_path))["features"]:
        p = f["properties"]
        if p["ADM0_A3"] in SKIP:
            continue
        en = p.get("NAME_EN") or p["NAME"]
        zh = (p.get("NAME_ZH") or en).strip()
        country = COUNTRY_ZH.get(p["ADM0NAME"]) or canon.get(p["ADM0NAME"].lower()) or canon.get((p.get("SOV0NAME") or "").lower()) \
            or canon.get(zh_country.get(p["ADM0_A3"], "").lower()) or zh_country.get(p["ADM0_A3"]) or p["ADM0NAME"]
        countries.setdefault(country, p["ADM0NAME"])
        lat, lon = round(p["LATITUDE"], 3), round(p["LONGITUDE"], 3)
        info = [p.get("ADM1NAME") or "", p.get("NAME_JA") or "", p.get("NAME_ZHT") or "", int(p.get("POP_MAX") or 0)]
        # only within the same country: a border town must not lend its state to the city across the river
        same = next((n for n, a, b, c in existing if c == country and ((zh == n and km((lat, lon), (a, b)) < 25) or km((lat, lon), (a, b)) < 8)), None)
        if same:
            # already listed (maybe under another spelling): just lend it the state and other names
            if same not in extra or extra[same][3] < info[3]:
                extra[same] = info
            continue
        out.append([zh, en, country, lat, lon, p.get("ADM1NAME") or "", p.get("NAME_JA") or "", p.get("NAME_ZHT") or "", int(p.get("POP_MAX") or 0)])
    out.sort(key=lambda r: -r[8])
    dest = root / "world_places.json"
    dest.write_text(json.dumps({"places": out, "extra": extra, "countries": countries}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(out)} places, {len(extra)} listed cities enriched, {dest.stat().st_size / 1024:.0f} KB")
    unmatched = sorted({r[2] for r in out if not re.search(r"[一-鿿]", r[2])})
    if unmatched:
        print("countries left in English:", unmatched)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
