"""从 Natural Earth 的一级行政区面数据生成 src/regions.json（「点亮」时填色用）。

数据：https://github.com/nvkelso/natural-earth-vector 的 geojson/ne_10m_admin_1_states_provinces.geojson（公有领域）
用法：python3 -I src/make_regions.py 下载好的.geojson [简化容差，单位度，默认 0.03]

每个区域是 [中文名, 英文名, 国家英文名, 多边形...]，多边形是若干个环，
每个环按 0.01° 取整后差分编码：[x0, y0, dx1, dy1, ...]。简化后太小的岛（少于 4 个点）丢掉，
但每个区域至少保留它最大的那一块。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from make_provinces import simplify  # noqa: E402

Q = 100


def encode(ring, tol):
    q = []
    for x, y in simplify([tuple(p[:2]) for p in ring], tol):
        p = (round(x * Q), round(y * Q))
        if not q or p != q[-1]:
            q.append(p)
    if len(q) < 4:
        return None
    enc = [q[0][0], q[0][1]]
    for (px, py), (x, y) in zip(q, q[1:]):
        enc += [x - px, y - py]
    return enc


def main(src, tol):
    out, total = [], 0
    for f in json.load(open(src))["features"]:
        g, p = f["geometry"], f["properties"]
        if not g:
            continue
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        kept = []
        for poly in polys:
            rings = [encode(r, tol) for r in poly]
            if rings[0]:
                kept.append([r for r in rings if r])
        if not kept:  # everything was tiny: keep the biggest piece anyway
            biggest = max(polys, key=lambda poly: len(poly[0]))
            kept = [[encode(biggest[0], 0) or []]]
        total += sum(len(r) // 2 for poly in kept for r in poly)
        out.append([p.get("name_zh") or p["name"], p.get("name_en") or p["name"], p["admin"], *kept])
    dest = Path(__file__).parent / "regions.json"
    dest.write_text(json.dumps({"q": Q, "regions": out}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(out)} regions, {total} points, {dest.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.03)
