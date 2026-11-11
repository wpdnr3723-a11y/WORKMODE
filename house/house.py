"""2층 단독주택 + 대지 모델 (text-to-cad / build123d).

좌표: X = 동(東), Y = 북(北), Z = 위. 모델 단위는 mm이고, 아래 치수는 m로 쓰고 M()으로 바꾼다.
대지: 경기도 성남시 분당구 운중동(서판교 단독주택단지), 제1종전용주거지역·지구단위계획구역.
     지번은 토지이음에서 확인해 채운다. 대지 형상은 대표 필지 15 m x 20 m (300 ㎡), 남측 6 m 도로로 가정.
법규 검토 수치는 house/check.py가 이 파일의 상수로 계산한다.
"""

import build123d as bd
from cad import model

# ---------------------------------------------------------------- 치수 (m)
LOT_W, LOT_D = 15.0, 20.0          # 대지 동서 x 남북
ROAD_W = 6.0                       # 남측 도로 폭

WALL = 0.30                        # 외벽 두께 (RC 200 + 단열·마감)
PART = 0.15                        # 내벽 두께
SLAB = 0.20                        # 2층 바닥 슬래브

GL = 0.0                           # 지표면
FL1 = 0.30                         # 1층 바닥 (지표 +300)
FL2 = 3.30                         # 2층 바닥 (층고 3.0 m)
TOP2 = 6.30                        # 2층 벽 상단 (처마)

# 1층 외곽 (동서 11 m x 남북 8 m) — 북측 경계에서 3.0 m 이격
B1 = (1.5, 9.0, 12.5, 17.0)        # x0, y0, x1, y1
# 2층 외곽 (동서 9 m x 남북 8 m) — 서측 2 m는 1층 지붕 위 테라스
B2 = (3.5, 9.0, 12.5, 17.0)
TERRACE = (1.5, 9.0, 3.5, 17.0)

ROOF_RISE_PER_RUN = 0.5            # 지붕 물매 1:2 (약 26.6°)
EAVE = 0.5                         # 처마 내밀기
ROOF_T = 0.20

RAIL_H = 1.2                       # 테라스 난간 높이 (건축법 시행령 제40조)

# 계단: ㄷ자, 17단, 단높이 176.5 mm, 단너비 260 mm, 너비 1.0 m
RISERS = 17
RISE = (FL2 - FL1) / RISERS
TREAD = 0.26
STAIR_W = 1.0
STAIR = (10.1, 13.62, 12.2, 16.7)  # 계단실 평면 범위 (x0, y0, x1, y1)

PARKING = [(9.4, 0.8), (12.0, 0.8)]  # 주차 2대, 각 2.5 x 5.0 m (일반형)
PARK_W, PARK_D = 2.5, 5.0

GARDEN = (0.5, 0.5, 8.9, 8.2)      # 앞마당 잔디·조경


def M(v):
    return v * 1000.0


# ---------------------------------------------------------------- 기본 도형
def box(x0, y0, z0, x1, y1, z1):
    """두 모서리(m)로 정한 직육면체."""
    a = bd.Align.MIN
    return bd.Pos(M(x0), M(y0), M(z0)) * bd.Box(
        M(x1 - x0), M(y1 - y0), M(z1 - z0), align=(a, a, a)
    )


def tag(shape, label, color):
    shape.label = label
    shape.color = color
    return shape


def shell(b, z0, z1, t=WALL):
    x0, y0, x1, y1 = b
    return box(x0, y0, z0, x1, y1, z1) - box(x0 + t, y0 + t, z0 - 1, x1 - t, y1 - t, z1 + 1)


# 외벽 개구부: (벽, 시작, 끝, 하단 z, 상단 z, 종류)  벽 = S/N/E/W, 시작·끝은 벽을 따라간 좌표(m)
OPEN_1F = [
    ("S", 2.3, 6.8, FL1 + 0.1, FL1 + 2.3, "win"),    # 거실 큰 창
    ("S", 8.2, 9.2, FL1 + 1.5, FL1 + 2.1, "win"),    # 화장실 고창
    ("S", 10.9, 11.9, FL1, FL1 + 2.1, "door"),       # 현관문
    ("N", 3.0, 5.4, FL1 + 1.0, FL1 + 2.1, "win"),    # 주방 창
    ("N", 8.2, 9.2, FL1 + 1.2, FL1 + 2.1, "win"),    # 다용도실 창
    ("W", 10.0, 12.5, FL1 + 0.9, FL1 + 2.2, "win"),  # 거실 서측 창
    ("W", 13.8, 15.8, FL1 + 0.9, FL1 + 2.2, "win"),  # 식당 서측 창
    ("E", 14.0, 15.4, FL1 + 2.0, FL1 + 2.6, "win"),  # 계단 창
]
OPEN_2F = [
    ("S", 4.3, 6.9, FL2 + 0.6, FL2 + 2.2, "win"),    # 안방 창
    ("S", 8.4, 11.4, FL2 + 0.9, FL2 + 2.2, "win"),   # 방2 창
    ("N", 6.0, 7.0, FL2 + 1.5, FL2 + 2.1, "win"),    # 욕실 고창
    ("N", 7.9, 9.7, FL2 + 0.9, FL2 + 2.1, "win"),    # 홀 창
    ("W", 10.3, 11.2, FL2, FL2 + 2.1, "door"),       # 안방 -> 테라스 문
    ("W", 11.6, 13.2, FL2 + 0.9, FL2 + 2.2, "win"),  # 안방 서측 창
    ("E", 10.0, 11.8, FL2 + 0.9, FL2 + 2.2, "win"),  # 방2 동측 창
]


def opening_box(b, wall, a0, a1, z0, z1, pad=0.0):
    """개구부 범위의 상자. pad=0이면 벽 두께 중앙의 얇은 유리·문짝용."""
    x0, y0, x1, y1 = b
    if pad:
        lo, hi = -pad, WALL + pad
    else:
        lo, hi = WALL / 2 - 0.02, WALL / 2 + 0.02
    if wall == "S":
        return box(a0, y0 + lo, z0, a1, y0 + hi, z1)
    if wall == "N":
        return box(a0, y1 - hi, z0, a1, y1 - lo, z1)
    if wall == "W":
        return box(x0 + lo, a0, z0, x0 + hi, a1, z1)
    return box(x1 - hi, a0, z0, x1 - lo, a1, z1)


def walls(b, z0, z1, openings, label):
    w = shell(b, z0, z1)
    for wall, a0, a1, oz0, oz1, _ in openings:
        w = w - opening_box(b, wall, a0, a1, oz0, oz1, pad=0.1)
    return tag(w, label, "#ece6da")


def fills(b, openings, kind, label, color):
    parts = [opening_box(b, w, a0, a1, z0, z1) for w, a0, a1, z0, z1, k in openings if k == kind]
    return tag(bd.Compound(children=parts), label, color) if parts else None


# ---------------------------------------------------------------- 내벽
# (x0, y0, x1, y1) 내벽, 문 자리는 벽을 끊어서 만든다. 높이는 층 바닥 ~ 위층 슬래브 하단.
PARTS_1F = [
    (7.5, 9.3, 7.65, 11.9), (7.5, 12.9, 7.65, 13.2), (7.5, 14.0, 7.65, 16.7),  # 거실·주방 | 홀
    (9.95, 9.3, 10.1, 11.65),                                              # 화장실 | 현관
    (7.65, 11.5, 8.2, 11.65), (9.0, 11.5, 10.4, 11.65), (11.3, 11.5, 12.2, 11.65),  # 화장실·현관 북측 (문, 중문)
    (9.95, 13.62, 10.1, 16.7),                                             # 계단실 서측
    (7.65, 14.15, 8.2, 14.3), (9.0, 14.15, 9.95, 14.3),                    # 다용도실 남측 (문)
]
PARTS_2F = [
    (7.5, 9.3, 7.65, 12.6), (7.5, 13.5, 7.65, 16.7),                      # 안방·욕실 | 홀 (안방 문)
    (7.65, 12.4, 8.0, 12.55), (8.9, 12.4, 12.2, 12.55),                    # 방2 북측 (문)
    (3.8, 13.6, 7.5, 13.75),                                               # 안방 | 드레스룸·욕실
    (5.5, 13.75, 5.65, 16.7),                                              # 드레스룸 | 욕실
]


def partitions(rects, z0, z1, label):
    parts = [box(*r[:2], z0, *r[2:], z1) for r in rects if r[2] > r[0] and r[3] > r[1]]
    return tag(bd.Compound(children=parts), label, "#f6f2ea")


# ---------------------------------------------------------------- 계단
def stair():
    x0, y0, x1, y1 = STAIR
    n1 = 9                       # 1차 계단 단수 (동측, 북쪽으로 오름)
    landing_z = FL1 + n1 * RISE
    steps = []
    # 1차: 동측 x1-W..x1, y0에서 북쪽으로
    for i in range(n1 - 1):
        ys = y0 + i * TREAD
        steps.append(box(x1 - STAIR_W, ys, FL1, x1, ys + TREAD, FL1 + (i + 1) * RISE))
    # 참: 북측 전폭
    land_y0 = y0 + (n1 - 1) * TREAD
    steps.append(box(x0, land_y0, FL1, x1, y1, landing_z))
    # 2차: 서측 x0..x0+W, 참에서 남쪽으로
    n2 = RISERS - n1
    for i in range(n2 - 1):
        ye = land_y0 - i * TREAD
        steps.append(box(x0, ye - TREAD, FL1, x0 + STAIR_W, ye, landing_z + (i + 1) * RISE))
    s = bd.Compound(children=steps)
    return tag(s, "stair", "#b98a5a")


# ---------------------------------------------------------------- 슬래브·지붕
def slabs():
    x0, y0, x1, y1 = B1
    ground = box(x0, y0, GL, x1, y1, FL1)
    floor2 = box(x0, y0, FL2 - SLAB, x1, y1, FL2) - box(*STAIR[:2], FL2 - SLAB - 1, *STAIR[2:], FL2 + 1)
    return tag(bd.Compound(children=[ground, floor2]), "slabs", "#bdb7ad")


def roof():
    x0, y0, x1, y1 = B2
    ym = (y0 + y1) / 2
    half = (y1 - y0) / 2 + EAVE
    rise = half * ROOF_RISE_PER_RUN
    z_eave = TOP2 - EAVE * ROOF_RISE_PER_RUN   # 처마 끝은 벽 상단보다 낮다

    def plane(sign):
        # 지붕판 단면 (YZ): 처마 끝 -> 용마루, 두께 ROOF_T
        ye = ym + sign * half
        pts = [
            (M(ye), M(z_eave)),
            (M(ym), M(z_eave + rise)),
            (M(ym), M(z_eave + rise + ROOF_T)),
            (M(ye), M(z_eave + ROOF_T)),
        ]
        sec = bd.Polyline(*pts, close=True)
        face = bd.make_face(sec)
        # XY 평면에 그린 (y, z) 단면을 YZ 평면으로 세운 뒤 X로 밀어낸다
        solid = bd.extrude(bd.Plane.YZ * face, amount=M(x1 - x0 + 2 * EAVE))
        return bd.Pos(M(x0 - EAVE), 0, 0) * solid

    r = bd.Compound(children=[plane(-1), plane(1)])
    return tag(r, "roof", "#5b5e66")


def gables():
    """박공벽: 2층 벽 위 삼각형 (동·서 측벽)."""
    x0, y0, x1, y1 = B2
    ym = (y0 + y1) / 2
    rise = (y1 - y0) / 2 * ROOF_RISE_PER_RUN
    tri = bd.make_face(bd.Polyline(
        (M(y0), M(TOP2)), (M(ym), M(TOP2 + rise)), (M(y1), M(TOP2)), close=True))
    tri = bd.Plane.YZ * tri
    west = bd.extrude(tri, amount=M(WALL))
    out = [bd.Pos(M(x0), 0, 0) * west, bd.Pos(M(x1 - WALL), 0, 0) * west]
    return tag(bd.Compound(children=out), "gables", "#ece6da")


def terrace_parapet():
    x0, y0, x1, y1 = TERRACE
    t = 0.15
    ring = box(x0, y0, FL2, x1 + 0.01, y1, FL2 + RAIL_H) - box(x0 + t, y0 + t, FL2 - 1, x1 + 1, y1 - t, FL2 + RAIL_H + 1)
    return tag(ring, "terrace_parapet_1200", "#ece6da")


# ---------------------------------------------------------------- 대지
def site():
    ground = tag(box(0, 0, -0.3, LOT_W, LOT_D, GL), "lot_300m2", "#cfc6b4")
    road = tag(box(-2, -ROAD_W, -0.32, LOT_W + 2, 0, -0.02), "road_6m", "#55585c")
    garden = tag(box(*GARDEN[:2], GL, *GARDEN[2:], GL + 0.02), "garden", "#7fae5a")
    north_garden = tag(box(0.5, 17.4, GL, 14.5, 19.5, GL + 0.02), "north_garden", "#7fae5a")
    pave = tag(box(9.2, 0, GL, 14.7, 8.9, GL + 0.03), "parking_pave", "#a7a49d")
    lines = []
    for px, py in PARKING:
        for dx in (0, PARK_W):
            lines.append(box(px + dx - 0.05, py, GL + 0.03, px + dx + 0.05, py + PARK_D, GL + 0.04))
    stripes = tag(bd.Compound(children=lines), "parking_2x_2.5x5.0", "#ffffff")
    # 생울타리 1.2 m (지구단위계획: 막힌 담장 대신 생울타리·투시형): 서·북·동 경계
    fence = tag(bd.Compound(children=[
        box(0, 0, GL, 0.6, LOT_D, 1.2),
        box(0, LOT_D - 0.6, GL, LOT_W, LOT_D, 1.2),
        box(LOT_W - 0.6, 9.0, GL, LOT_W, LOT_D, 1.2),
    ]), "hedge_1200", "#5e8f45")
    trees = []
    for x, y, h in [(1.6, 1.6, 4.0), (5.0, 1.4, 3.2), (1.4, 6.5, 3.6), (13.0, 18.5, 4.2), (3.0, 18.6, 3.8)]:
        trunk = bd.Pos(M(x), M(y), 0) * bd.Cylinder(120, M(h * 0.5), align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        crown = bd.Pos(M(x), M(y), M(h * 0.65)) * bd.Sphere(M(h * 0.28))
        trees += [tag(trunk, "trunk", "#6b4a2b"), tag(crown, "crown", "#4f8a3c")]
    return [ground, road, garden, north_garden, pave, stripes, fence,
            tag(bd.Compound(children=trees), "trees", "#4f8a3c")]


# ---------------------------------------------------------------- 조립
@model
def house():
    parts = site()
    parts += [
        slabs(),
        walls(B1, GL, FL2, OPEN_1F, "walls_1f"),
        walls(B2, FL2, TOP2, OPEN_2F, "walls_2f"),
        gables(),
        roof(),
        terrace_parapet(),
        partitions(PARTS_1F, FL1, FL2 - SLAB, "partitions_1f"),
        partitions(PARTS_2F, FL2, TOP2, "partitions_2f"),
        stair(),
    ]
    for b, ops, n in ((B1, OPEN_1F, "1f"), (B2, OPEN_2F, "2f")):
        for kind, color in (("win", "#8fc3e6aa"), ("door", "#6d4c35")):
            f = fills(b, ops, kind, f"{kind}s_{n}", color)
            if f is not None:
                parts.append(f)
    return bd.Compound(children=parts, label="house_seopangyo_unjung_300m2")


if __name__ == "__main__":
    house()
