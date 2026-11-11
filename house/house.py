"""2층 단독주택 + 대지 3D 모델 (text-to-cad / build123d).  실행: cad run house.py

설계값은 spec.py에 있고, 도면(drawings.py)과 법규 검토(check.py)도 같은 값을 쓴다.
모델 단위는 mm이고 spec의 m 값을 M()으로 바꾼다.
"""

import build123d as bd
from cad import model

from spec import (B1, B2, BEAMS, DOOR_H, EAVE, FL1, FL2, FOOT_BOT, FOOT_W, GARDEN, GL, HEDGE_T,
                  LANDING_Y, LOT_D, LOT_W, MAT_BOT, MAT_TOP, N1, NORTH_GARDEN, PARK_D, PARK_W,
                  PARKING, RAIL_H, RAILS_2F, RIDGE_BEAM, RIDGE_Y, RISE, RISERS, ROAD_W, ROOF_PITCH,
                  ROOF_T, SLAB, SLAB_OPENINGS, SLAB_RC, STAIR, STAIR_W, TERRACE, TERRACE_DROP, TOP2,
                  TREAD, WALL, Z_EAVE, Z_RIDGE_UNDER, openings, parts)


def M(v):
    return v * 1000.0


def box(x0, y0, z0, x1, y1, z1):
    a = bd.Align.MIN
    return bd.Pos(M(x0), M(y0), M(z0)) * bd.Box(M(x1 - x0), M(y1 - y0), M(z1 - z0), align=(a, a, a))


def tag(shape, label, color):
    shape.label = label
    shape.color = color
    return shape


def group(items, label, color):
    return tag(bd.Compound(children=list(items)), label, color)


# ---------------------------------------------------------------- 외벽
def opening_box(b, o, pad):
    x0, y0, x1, y1 = b
    lo, hi = (-pad, WALL + pad) if pad else (WALL / 2 - 0.02, WALL / 2 + 0.02)
    w, a0, a1, z0, z1 = o["wall"], o["a0"], o["a1"], o["z0"], o["z1"]
    if w == "S":
        return box(a0, y0 + lo, z0, a1, y0 + hi, z1)
    if w == "N":
        return box(a0, y1 - hi, z0, a1, y1 - lo, z1)
    if w == "W":
        return box(x0 + lo, a0, z0, x0 + hi, a1, z1)
    return box(x1 - hi, a0, z0, x1 - lo, a1, z1)


def walls(b, z0, z1, floor):
    x0, y0, x1, y1 = b
    w = box(x0, y0, z0, x1, y1, z1) - box(x0 + WALL, y0 + WALL, z0 - 1, x1 - WALL, y1 - WALL, z1 + 1)
    for o in openings(floor):
        w = w - opening_box(b, o, 0.1)
    return tag(w, f"walls_{floor}f", "#ece6da")


def fills(b, floor, kind, color):
    items = [opening_box(b, o, 0) for o in openings(floor) if o["kind"] == kind]
    return group(items, f"{kind}s_{floor}f", color) if items else None


# ---------------------------------------------------------------- 내벽 (문 자리 제외)
def partitions(floor, z0, z1):
    out = []
    for p in parts(floor):
        x0, y0, x1, y1 = p["rect"]
        w = box(x0, y0, z0, x1, y1, z1)
        along_y = (y1 - y0) > (x1 - x0)
        for a0, a1, _, _, kind, _ in p["doors"]:
            top = z1 + 1 if kind == "open" else z0 + DOOR_H
            if along_y:
                w = w - box(x0 - 0.1, a0, z0 - 0.1, x1 + 0.1, a1, top)
            else:
                w = w - box(a0, y0 - 0.1, z0 - 0.1, a1, y1 + 0.1, top)
        out.append(w)
    return group(out, f"partitions_{floor}f", "#f6f2ea")


# ---------------------------------------------------------------- 계단
def stair():
    x0, y0, x1, y1 = STAIR
    landing_z = FL1 + N1 * RISE
    steps = []
    for i in range(N1 - 1):                       # 1차: 동측, 북쪽으로 오름
        ys = y0 + i * TREAD
        steps.append(box(x1 - STAIR_W, ys, FL1, x1, ys + TREAD, FL1 + (i + 1) * RISE))
    steps.append(box(x0, LANDING_Y, FL1, x1, y1, landing_z))      # 참
    for i in range(RISERS - N1 - 1):              # 2차: 서측, 남쪽으로 오름
        ye = LANDING_Y - i * TREAD
        steps.append(box(x0, ye - TREAD, FL1, x0 + STAIR_W, ye, landing_z + (i + 1) * RISE))
    return group(steps, "stair", "#b98a5a")


# ---------------------------------------------------------------- 구조체
def foundation():
    x0, y0, x1, y1 = B1
    mat = box(x0, y0, MAT_BOT, x1, y1, MAT_TOP)
    ring = box(x0, y0, FOOT_BOT, x1, y1, MAT_BOT) - box(x0 + FOOT_W, y0 + FOOT_W, FOOT_BOT - 1,
                                                         x1 - FOOT_W, y1 - FOOT_W, MAT_BOT + 1)
    build_up = box(x0 + WALL, y0 + WALL, MAT_TOP, x1 - WALL, y1 - WALL, FL1)
    return [tag(mat + ring, "foundation_F1_FG1", "#a9a39a"), tag(build_up, "floor_1f_buildup", "#d9cbb0")]


def slab_2f():
    x0, y0, x1, y1 = B1
    tx1 = TERRACE[2]
    s = box(tx1, y0, FL2 - SLAB, x1, y1, FL2)
    for o in SLAB_OPENINGS:
        s = s - box(o[0], o[1], FL2 - SLAB - 1, o[2], o[3], FL2 + 1)
    z2 = FL2 - SLAB - TERRACE_DROP
    terrace = box(x0, y0, z2, tx1, y1, z2 + SLAB_RC)
    deck = box(x0 + 0.15, y0 + 0.15, z2 + SLAB_RC, tx1, y1 - 0.15, FL2 - 0.05)
    return [tag(s, "slab_S1", "#bdb7ad"), tag(terrace, "slab_S2_terrace", "#bdb7ad"),
            tag(deck, "terrace_deck", "#9b7b5b")]


def beams():
    top = FL2 - (SLAB - SLAB_RC)          # 슬래브 RC 상단
    out = []
    for b in BEAMS:
        hb = b["b"] / 2
        if b["axis"] == "x":
            out.append(box(b["r0"], b["at"] - hb, top - b["h"], b["r1"], b["at"] + hb, top))
        else:
            out.append(box(b["at"] - hb, b["r0"], top - b["h"], b["at"] + hb, b["r1"], top))
    x0, _, x1, _ = B2
    rb = RIDGE_BEAM
    out.append(box(x0 + WALL, RIDGE_Y - rb["b"] / 2, Z_RIDGE_UNDER - rb["h"],
                   x1 - WALL, RIDGE_Y + rb["b"] / 2, Z_RIDGE_UNDER))
    return group(out, "beams_G1_B1_TG1_RB1", "#9d968c")


def roof():
    x0, y0, x1, y1 = B2
    half = (y1 - y0) / 2 + EAVE
    rise = half * ROOF_PITCH

    def plane(sign):
        ye = RIDGE_Y + sign * half
        pts = [(M(ye), M(Z_EAVE)), (M(RIDGE_Y), M(Z_EAVE + rise)),
               (M(RIDGE_Y), M(Z_EAVE + rise + ROOF_T)), (M(ye), M(Z_EAVE + ROOF_T))]
        face = bd.Plane.YZ * bd.make_face(bd.Polyline(*pts, close=True))
        return bd.Pos(M(x0 - EAVE), 0, 0) * bd.extrude(face, amount=M(x1 - x0 + 2 * EAVE))

    return group([plane(-1), plane(1)], "roof_RS1", "#5b5e66")


def gables():
    x0, y0, x1, y1 = B2
    tri = bd.make_face(bd.Polyline((M(y0), M(TOP2)), (M(RIDGE_Y), M(Z_RIDGE_UNDER)), (M(y1), M(TOP2)), close=True))
    w = bd.extrude(bd.Plane.YZ * tri, amount=M(WALL))
    return group([bd.Pos(M(x0), 0, 0) * w, bd.Pos(M(x1 - WALL), 0, 0) * w], "gables", "#ece6da")


def terrace_parapet():
    x0, y0, x1, y1 = TERRACE
    t = 0.15
    z0 = FL2 - SLAB - TERRACE_DROP
    ring = box(x0, y0, z0, x1 + 0.01, y1, FL2 + RAIL_H) - box(x0 + t, y0 + t, z0 - 1, x1 + 1, y1 - t, FL2 + RAIL_H + 1)
    return tag(ring, "terrace_parapet_1200", "#ece6da")


def rails():
    out = []
    for (ax, ay), (bx, by) in RAILS_2F:
        out.append(box(min(ax, bx) - 0.02, min(ay, by) - 0.02, FL2,
                       max(ax, bx) + 0.02, max(ay, by) + 0.02, FL2 + RAIL_H))
    return group(out, "stair_rail_1200", "#7c7f86")


# ---------------------------------------------------------------- 대지
def site():
    ground = tag(box(0, 0, -0.3, LOT_W, LOT_D, GL), "lot_290m2", "#cfc6b4")
    road = tag(box(-2, -ROAD_W, -0.32, LOT_W + 2, 0, -0.02), "road_6m", "#55585c")
    garden = tag(box(*GARDEN[:2], GL, *GARDEN[2:], GL + 0.02), "garden", "#7fae5a")
    north = tag(box(*NORTH_GARDEN[:2], GL, *NORTH_GARDEN[2:], GL + 0.02), "north_garden", "#7fae5a")
    pave = tag(box(9.1, 0, GL, LOT_W - 0.05, 8.9, GL + 0.03), "parking_pave", "#a7a49d")
    lines = [box(px + dx - 0.05, py, GL + 0.03, px + dx + 0.05, py + PARK_D, GL + 0.04)
             for px, py in PARKING for dx in (0, PARK_W)]
    hedge = group([box(0, 0, GL, HEDGE_T, LOT_D, 1.2), box(0, LOT_D - HEDGE_T, GL, LOT_W, LOT_D, 1.2),
                   box(LOT_W - HEDGE_T, 9.0, GL, LOT_W, LOT_D, 1.2)], "hedge_1200", "#5e8f45")
    trees = []
    for x, y, h in [(1.6, 1.6, 4.0), (5.0, 1.4, 3.2), (1.4, 6.5, 3.6), (12.6, 18.4, 4.2), (3.0, 18.6, 3.8)]:
        trees.append(bd.Pos(M(x), M(y), 0) * bd.Cylinder(120, M(h * 0.5), align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)))
        trees.append(bd.Pos(M(x), M(y), M(h * 0.65)) * bd.Sphere(M(h * 0.28)))
    return [ground, road, garden, north, pave, group(lines, "parking_2x_2.5x5.0", "#ffffff"), hedge,
            group(trees, "trees", "#4f8a3c")]


@model
def house():
    items = site() + foundation() + slab_2f()
    items += [
        walls(B1, MAT_TOP, FL2, 1),
        walls(B2, FL2, TOP2, 2),
        gables(), roof(), beams(), terrace_parapet(), rails(),
        partitions(1, FL1, FL2 - SLAB),
        partitions(2, FL2, TOP2),
        stair(),
    ]
    for b, floor in ((B1, 1), (B2, 2)):
        for kind, color in (("win", "#8fc3e6aa"), ("door", "#6d4c35")):
            f = fills(b, floor, kind, color)
            if f is not None:
                items.append(f)
    return bd.Compound(children=items, label="house_gyeongsan4_jinryang_290m2")


if __name__ == "__main__":
    house()
