"""把 src/page.html 和地图数据、依赖库合成一个独立的 index.html。用法：python3 build.py"""
import json
from pathlib import Path

root = Path(__file__).parent
src = root / "src"


def compact(name):
    return json.dumps(json.loads((src / name).read_text()), separators=(",", ":"), ensure_ascii=False)


page = (src / "page.html").read_text()
parts = {
    "__D3_ARRAY__": (src / "vendor/d3-array.min.js").read_text(),
    "__D3_GEO__": (src / "vendor/d3-geo.min.js").read_text(),
    "__TOPOJSON__": (src / "vendor/topojson-client.min.js").read_text(),
    "__WORLD50__": compact("c50.json"),
    "__WORLD110__": compact("c110.json"),
    "__PROVINCES__": compact("provinces.json"),
    "__WORLD_PLACES__": compact("world_places.json"),
    "__REGIONS__": compact("regions.json"),
}
for key, value in parts.items():
    assert page.count(key) == 1, key
    page = page.replace(key, value)
(root / "index.html").write_text(page)
print(f"index.html: {len(page.encode()) / 1024:.0f} KB")
