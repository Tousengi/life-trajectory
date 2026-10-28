"""从 Natural Earth 的一级行政区边界线生成 src/provinces.json（页面里画省界用）。

数据：https://github.com/nvkelso/natural-earth-vector 的 geojson/ne_10m_admin_1_states_provinces_lines.geojson（公有领域）
用法：python3 -I src/make_provinces.py 下载好的.geojson [简化容差，单位度，默认 0.02]

只留 MIN_ZOOM ≤ 7 的边界（中国的省、日本的县都在里面，英国郡这类细碎的不要），
先把首尾相接的碎段连成长线，再用 Douglas-Peucker 简化，
坐标按 0.01° 取整后差分编码：每条线是 [x0, y0, dx1, dy1, ...]。
"""
import json
import sys
from pathlib import Path

MAX_ZOOM = 7
Q = 100  # 0.01°


def simplify(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        norm = (dx * dx + dy * dy) ** 0.5
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            x, y = pts[i]
            d = abs(dy * (x - x1) - dx * (y - y1)) / norm if norm else ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
            if d > best:
                best, idx = d, i
        if best > tol:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def chain(parts):
    """把首尾相接的碎段连成长线（数据里一条省界常被切成几十段）。"""
    key = lambda p: (round(p[0] * 1e4), round(p[1] * 1e4))
    ends = {}
    for i, part in enumerate(parts):
        for e in (0, -1):
            ends.setdefault(key(part[e]), []).append(i)
    used, out = set(), []
    for i in range(len(parts)):
        if i in used:
            continue
        used.add(i)
        line = list(parts[i])
        for forward in (True, False):
            while True:
                tip = key(line[-1] if forward else line[0])
                nxt = next((j for j in ends.get(tip, []) if j not in used), None)
                if nxt is None:
                    break
                used.add(nxt)
                seg = parts[nxt] if key(parts[nxt][0]) == tip else parts[nxt][::-1]
                # seg starts at the tip: append its rest, or prepend it reversed
                line = line + seg[1:] if forward else seg[:0:-1] + line
        out.append(line)
    return out


def main(src, tol):
    raw = []
    for f in json.load(open(src))["features"]:
        g = f["geometry"]
        if not g or f["properties"]["MIN_ZOOM"] > MAX_ZOOM:
            continue
        for part in (g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]):
            raw.append([tuple(p[:2]) for p in part])
    lines, total = [], 0
    for part in chain(raw):
        q = []
        for x, y in simplify(part, tol):
            p = (round(x * Q), round(y * Q))
            if not q or p != q[-1]:
                q.append(p)
        if len(q) < 2:
            continue
        enc = [q[0][0], q[0][1]]
        for (px, py), (x, y) in zip(q, q[1:]):
            enc += [x - px, y - py]
        lines.append(enc)
        total += len(q)
    out = Path(__file__).parent / "provinces.json"
    out.write_text(json.dumps({"q": Q, "lines": lines}, separators=(",", ":")))
    print(f"{len(raw)} pieces -> {len(lines)} lines, {total} points, {out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.02)
