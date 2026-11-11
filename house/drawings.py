# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "shapely>=2.0", "koreanize-matplotlib>=0.1.1", "setuptools"]
# ///
"""건축 도면 세트 (A2 PDF, A3 축소 출력 가능).  실행: uv run drawings.py  ->  drawings/house_drawings.pdf

모든 치수는 spec.py에서 온다. 3D 모델(house.py)과 같은 값이므로 설계를 바꾸면 둘 다 함께 바뀐다.
"""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Arc, Circle, PathPatch, Polygon as MPoly  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from shapely.geometry import Polygon, box as sbox  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

import spec as S  # noqa: E402
from check import ROWS, SUMMARY  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "drawings"
DATE = "2026. 11."

# ---------------------------------------------------------------- 글꼴 (나눔고딕, koreanize-matplotlib 동봉)
import logging  # noqa: E402

import koreanize_matplotlib  # noqa: E402,F401

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
plt.rcParams.update({"pdf.fonttype": 42, "hatch.linewidth": 0.25, "axes.unicode_minus": False})

PT = 72 / 25.4                                     # mm -> pt
LW = dict(cut=0.50, heavy=0.35, vis=0.25, thin=0.18, fine=0.13)
RC_FC, INS_FC, PART_FC = "#d9d9d9", "#fff4c2", "#efefef"


def fs(mm):
    return mm * 3.9                                # 글자 높이(mm) -> pt


def mm(v):
    return f"{round(v * 1000):,}"


# ---------------------------------------------------------------- 시트·뷰
class View:
    def __init__(self, ax, ox, oy, scale, u0=0.0, v0=0.0):
        self.ax, self.ox, self.oy, self.k, self.u0, self.v0 = ax, ox, oy, 1000.0 / scale, u0, v0

    def P(self, u, v):
        return (self.ox + (u - self.u0) * self.k, self.oy + (v - self.v0) * self.k)

    # 기본 도형
    def line(self, pts, lw="vis", ls="-", color="k", z=4):
        xy = [self.P(*p) for p in pts]
        self.ax.plot([p[0] for p in xy], [p[1] for p in xy], color=color, lw=LW.get(lw, lw) * PT,
                     ls=ls, zorder=z, solid_capstyle="butt")

    def poly(self, pts, fc="none", ec="k", lw="vis", hatch=None, z=2, ls="-", alpha=1):
        self.ax.add_patch(MPoly([self.P(*p) for p in pts], closed=True, fc=fc, ec=ec, ls=ls,
                                lw=LW.get(lw, lw) * PT, hatch=hatch, zorder=z, alpha=alpha))

    def rect(self, u0, v0, u1, v1, **kw):
        self.poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], **kw)

    def geom(self, g, fc="none", ec="k", lw="vis", hatch=None, z=2, ls="-"):
        if g.is_empty:
            return
        polys = [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
        for p in polys:
            verts, codes = [], []
            for ring in [p.exterior, *p.interiors]:
                pts = [self.P(*c) for c in ring.coords]
                verts += pts
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2) + [MPath.CLOSEPOLY]
            self.ax.add_patch(PathPatch(MPath(verts, codes), fc=fc, ec=ec, lw=LW.get(lw, lw) * PT,
                                        hatch=hatch, zorder=z, ls=ls))

    def solid(self, g, fc=RC_FC, hatch="////", z=2, lw="cut"):
        """절단면: 채움 + 해치(외곽선 없이) 후 외곽선."""
        self.geom(g, fc=fc, ec="#555555", lw=0, hatch=hatch, z=z)
        self.geom(g, fc="none", ec="k", lw=lw, z=z + 0.5)

    def text(self, u, v, s, size=2.5, ha="center", va="center", rot=0, color="k", z=6, weight="normal", bg=None):
        x, y = self.P(u, v)
        t = self.ax.text(x, y, s, fontsize=fs(size), ha=ha, va=va, rotation=rot, color=color, zorder=z,
                         fontweight=weight)
        if bg:
            t.set_bbox(dict(fc=bg, ec="none", pad=0.4))
        return t

    def arc(self, u, v, r, t1, t2, lw="thin", ls="-"):
        x, y = self.P(u, v)
        d = 2 * r * self.k
        self.ax.add_patch(Arc((x, y), d, d, theta1=t1, theta2=t2, lw=LW[lw] * PT, ls=ls, zorder=4))

    def bubble(self, u, v, label, r=3.5):
        x, y = self.P(u, v)
        self.ax.add_patch(Circle((x, y), r, fc="white", ec="k", lw=LW["vis"] * PT, zorder=7))
        self.ax.text(x, y, label, fontsize=fs(2.3), ha="center", va="center", zorder=8)

    # 치수 (모델 좌표, 값은 mm)
    def hdim(self, us, v, ext=None, size=1.9, gap=1.0):
        """us: 위치들(연속 치수). v: 치수선 위치. ext: 보조선이 시작하는 v (도형 위치)."""
        us = sorted(set(round(u, 4) for u in us))
        y = self.P(0, v)[1]
        x0, x1 = self.P(us[0], v)[0], self.P(us[-1], v)[0]
        self.ax.plot([x0 - 1.5, x1 + 1.5], [y, y], color="k", lw=LW["fine"] * PT, zorder=5)
        for u in us:
            x = self.P(u, v)[0]
            if ext is not None:
                ye = self.P(0, ext)[1]
                d = 1 if y > ye else -1
                self.ax.plot([x, x], [ye + d * gap, y + d * 1.5], color="k", lw=LW["fine"] * PT, zorder=5)
            self.ax.plot([x - 0.8, x + 0.8], [y - 0.8, y + 0.8], color="k", lw=LW["thin"] * PT, zorder=5)
        for a, b in zip(us, us[1:]):
            xm = (self.P(a, v)[0] + self.P(b, v)[0]) / 2
            w = self.P(b, v)[0] - self.P(a, v)[0]
            txt = mm(b - a)
            self.ax.text(xm, y + 0.6, txt, fontsize=fs(size if w > len(txt) * size * 0.75 else size * 0.75),
                         ha="center", va="bottom", zorder=6)

    def vdim(self, vs, u, ext=None, size=1.9, gap=1.0):
        vs = sorted(set(round(v, 4) for v in vs))
        x = self.P(u, 0)[0]
        y0, y1 = self.P(u, vs[0])[1], self.P(u, vs[-1])[1]
        self.ax.plot([x, x], [y0 - 1.5, y1 + 1.5], color="k", lw=LW["fine"] * PT, zorder=5)
        for v in vs:
            y = self.P(u, v)[1]
            if ext is not None:
                xe = self.P(ext, 0)[0]
                d = 1 if x > xe else -1
                self.ax.plot([xe + d * gap, x + d * 1.5], [y, y], color="k", lw=LW["fine"] * PT, zorder=5)
            self.ax.plot([x - 0.8, x + 0.8], [y - 0.8, y + 0.8], color="k", lw=LW["thin"] * PT, zorder=5)
        for a, b in zip(vs, vs[1:]):
            ym = (self.P(u, a)[1] + self.P(u, b)[1]) / 2
            h = self.P(u, b)[1] - self.P(u, a)[1]
            txt = mm(b - a)
            self.ax.text(x - 0.6, ym, txt, fontsize=fs(size if h > len(txt) * size * 0.75 else size * 0.75),
                         ha="right", va="center", rotation=90, zorder=6)

    def level(self, u, v, label, side="right", length=18):
        x, y = self.P(u, v)
        d = 1 if side == "right" else -1
        self.ax.plot([x, x + d * length], [y, y], color="k", lw=LW["thin"] * PT, zorder=5)
        tri = [(x + d * 3, y), (x + d * 1.6, y + 2.2), (x + d * 4.4, y + 2.2)]
        self.ax.add_patch(MPoly(tri, closed=True, fc="k", ec="k", lw=0.2, zorder=6))
        self.ax.text(x + d * 5.5, y + 0.7, label, fontsize=fs(2.0), ha="left" if d > 0 else "right",
                     va="bottom", zorder=6)

    def leader(self, u, v, tx, ty, s, size=2.0, ha="left"):
        """(u, v) 모델 점에서 (tx, ty) 시트 좌표의 글자로 지시선."""
        x, y = self.P(u, v)
        self.ax.plot([x, tx], [y, ty], color="k", lw=LW["fine"] * PT, zorder=6)
        self.ax.add_patch(Circle((x, y), 0.45, fc="k", ec="none", zorder=6))
        self.ax.plot([tx, tx + (2 if ha == "left" else -2)], [ty, ty], color="k", lw=LW["fine"] * PT, zorder=6)
        self.ax.text(tx + (2.6 if ha == "left" else -2.6), ty, s, fontsize=fs(size), ha=ha, va="center", zorder=6)


class Sheet:
    W, H = 594.0, 420.0                           # A2
    TB = (414.0, 10.0, 584.0, 46.0)               # 표제란

    def __init__(self, book, no, title, scale):
        self.book, self.no, self.title, self.scale = book, no, title, scale
        self.fig = plt.figure(figsize=(self.W / 25.4, self.H / 25.4))
        ax = self.fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, self.W)
        ax.set_ylim(0, self.H)
        ax.set_aspect("equal")
        ax.axis("off")
        self.ax = ax
        self.frame()

    def view(self, ox, oy, scale, u0=0.0, v0=0.0):
        return View(self.ax, ox, oy, scale, u0, v0)

    def text(self, x, y, s, size=2.5, ha="left", va="center", weight="normal", color="k", rot=0):
        return self.ax.text(x, y, s, fontsize=fs(size), ha=ha, va=va, fontweight=weight, color=color,
                            rotation=rot, zorder=8)

    def hline(self, x0, x1, y, lw="thin"):
        self.ax.plot([x0, x1], [y, y], color="k", lw=LW[lw] * PT, zorder=7)

    def vline(self, x, y0, y1, lw="thin"):
        self.ax.plot([x, x], [y0, y1], color="k", lw=LW[lw] * PT, zorder=7)

    def frame(self):
        ax = self.ax
        ax.add_patch(MPoly([(10, 10), (self.W - 10, 10), (self.W - 10, self.H - 10), (10, self.H - 10)], closed=True, fc="none", ec="k",
                           lw=0.7 * PT, zorder=7))
        x0, y0, x1, y1 = self.TB
        ax.add_patch(MPoly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True, fc="white", ec="k",
                           lw=0.5 * PT, zorder=7))
        rows = [y0, y0 + 9, y0 + 18, y0 + 27, y1]
        for y in rows[1:-1]:
            self.hline(x0, x1, y)
        self.vline(x0 + 22, y0, y1)
        self.vline(x0 + 108, y0, y0 + 18)
        self.vline(x0 + 128, y0, y0 + 18)
        lab = [("공 사 명", S.PROJECT), ("도 면 명", self.title), ("도면번호", self.no), ("일    자", DATE)]
        self.text(x0 + 11, y0 + 31.5, "공 사 명", 2.0, ha="center")
        self.text(x0 + 25, y0 + 31.5, S.PROJECT, 2.8, weight="bold")
        self.text(x0 + 11, y0 + 22.5, "도 면 명", 2.0, ha="center")
        self.text(x0 + 25, y0 + 22.5, self.title, 3.0, weight="bold")
        self.text(x0 + 11, y0 + 13.5, "도면번호", 2.0, ha="center")
        self.text(x0 + 25, y0 + 13.5, self.no, 3.0, weight="bold")
        self.text(x0 + 118, y0 + 13.5, "축 척", 2.0, ha="center")
        self.text(x0 + 144, y0 + 13.5, self.scale, 2.4, ha="center")
        self.text(x0 + 11, y0 + 4.5, "일    자", 2.0, ha="center")
        self.text(x0 + 25, y0 + 4.5, DATE, 2.4)
        self.text(x0 + 118, y0 + 4.5, "설 계", 2.0, ha="center")
        self.text(x0 + 144, y0 + 4.5, "건축사 (미정)", 2.2, ha="center")
        del lab
        self.text(14, 13, "※ 인허가·실시설계 검토용 초안입니다. 건축사·구조기술사의 검토와 날인 전에는 시공·제출에 쓰지 않습니다. "
                  "치수 단위 mm, 레벨 기준 GL±0 (설계 지반고).", 1.9, color="#444444")

    def heading(self, x, y, title, scale=None, num=None):
        if num:
            self.ax.add_patch(Circle((x + 4, y), 4, fc="white", ec="k", lw=LW["vis"] * PT, zorder=7))
            self.text(x + 4, y, num, 2.4, ha="center")
            x += 10
        self.text(x, y + 0.6, title, 3.6, weight="bold", va="bottom")
        self.hline(x, x + 75, y - 0.2, "heavy")
        if scale:
            self.text(x, y - 1.5, f"SCALE {scale}", 2.0, va="top")

    def table(self, x, y, widths, rows, rh=6.0, size=2.1, head=True, aligns=None):
        """y = 표 윗변. rows[0]이 머리글."""
        total = sum(widths)
        n = len(rows)
        if head:
            self.ax.add_patch(MPoly([(x, y), (x + total, y), (x + total, y - rh), (x, y - rh)], closed=True,
                                    fc="#eeeeee", ec="none", zorder=6))
        for i in range(n + 1):
            self.hline(x, x + total, y - i * rh, "heavy" if i in (0, n) or (head and i == 1) else "fine")
        cx = x
        for w in widths:
            self.vline(cx, y - n * rh, y, "fine")
            cx += w
        self.vline(cx, y - n * rh, y, "fine")
        for i, row in enumerate(rows):
            cx = x
            for j, (w, cell) in enumerate(zip(widths, row)):
                a = (aligns[j] if aligns else "left") if not (head and i == 0) else "center"
                tx = cx + 1.2 if a == "left" else (cx + w / 2 if a == "center" else cx + w - 1.2)
                s = str(cell)
                sz = size
                while len(s) * sz * 0.92 > w - 2 and sz > 1.2:
                    sz -= 0.1
                self.text(tx, y - (i + 0.5) * rh, s, sz, ha=a, weight="bold" if head and i == 0 else "normal")
                cx += w
        return y - n * rh

    def north(self, x, y, r=7):
        self.ax.add_patch(Circle((x, y), r, fc="none", ec="k", lw=LW["vis"] * PT, zorder=7))
        self.ax.add_patch(MPoly([(x, y + r + 2), (x - 2.5, y - r * 0.6), (x, y - r * 0.2)], closed=True,
                                fc="k", ec="k", lw=0.2, zorder=8))
        self.ax.add_patch(MPoly([(x, y + r + 2), (x + 2.5, y - r * 0.6), (x, y - r * 0.2)], closed=True,
                                fc="white", ec="k", lw=0.3 * PT, zorder=8))
        self.text(x, y + r + 4.5, "N", 3.0, ha="center", weight="bold")

    def save(self):
        self.book.savefig(self.fig)
        plt.close(self.fig)


# ---------------------------------------------------------------- 공통 기하
def iv_sub(lo, hi, cuts):
    """[lo, hi]에서 cuts 구간들을 뺀 구간 목록."""
    out = [(lo, hi)]
    for a, b in cuts:
        nxt = []
        for c, d in out:
            if b <= c or a >= d:
                nxt.append((c, d))
            else:
                if a > c:
                    nxt.append((c, a))
                if b < d:
                    nxt.append((b, d))
        out = nxt
    return [(c, d) for c, d in out if d - c > 1e-6]


def band(b, side, o0, o1, a, c):
    """외벽 면(side)에서 안쪽으로 o0..o1 깊이, 벽 방향 a..c 구간의 사각형."""
    x0, y0, x1, y1 = b
    if side == "S":
        return sbox(a, y0 + o0, c, y0 + o1)
    if side == "N":
        return sbox(a, y1 - o1, c, y1 - o0)
    if side == "W":
        return sbox(x0 + o0, a, x0 + o1, c)
    return sbox(x1 - o1, a, x1 - o0, c)


def side_range(b, side):
    x0, y0, x1, y1 = b
    return (x0, x1) if side in "SN" else (y0, y1)


O_INS0, O_INS1 = 0.0, S.W_FIN + S.W_INS                   # 0 ~ 0.11
O_RC0, O_RC1 = O_INS1, O_INS1 + S.W_RC                    # 0.11 ~ 0.29


# ---------------------------------------------------------------- 평면도
CUT_H = 1.2


def plan_walls(v, b, floor, fl, sides="SNEW"):
    ops = [o for o in S.openings(floor) if o["wall"] in sides]
    cut = [o for o in ops if o["z0"] - fl < CUT_H]
    rc, ins = [], []
    for side in sides:
        lo, hi = side_range(b, side)
        holes = [(o["a0"], o["a1"]) for o in cut if o["wall"] == side]
        for a, c in iv_sub(lo, hi, holes):
            rc.append(band(b, side, O_RC0, S.WALL, a, c))
            ins.append(band(b, side, O_INS0, O_INS1, a, c))
    rc_u, ins_u = unary_union(rc), unary_union(ins)
    whole = unary_union(rc + ins)
    rc_only = rc_u.difference(ins_u)
    v.geom(rc_only, fc=RC_FC, ec="#555555", lw=0, hatch="////", z=2)
    v.geom(ins_u, fc=INS_FC, ec="#b08a00", lw=0, hatch="....", z=2)
    v.geom(ins_u, fc="none", ec="k", lw="fine", z=2.4)
    v.geom(whole, fc="none", ec="k", lw="cut", z=2.5)
    # 개구부
    for o in ops:
        side, a0, a1 = o["wall"], o["a0"], o["a1"]
        if o not in cut:                                    # 절단 높이 위 창 (점선)
            g = band(b, side, 0, S.WALL, a0, a1)
            v.geom(g, fc="none", ec="k", lw="thin", ls="--", z=3)
            continue
        if o["kind"] == "win":
            for off, lw in ((0.0, "thin"), (S.WALL / 2 - 0.03, "vis"), (S.WALL / 2 + 0.03, "vis"), (S.WALL, "thin")):
                g = band(b, side, off, off, a0, a1)
                x0, y0, x1, y1 = g.bounds
                v.line([(x0, y0), (x1, y1)], lw=lw, z=3)
            if a1 - a0 > 1.4:
                g = band(b, side, S.WALL / 2 - 0.03, S.WALL / 2 + 0.03, (a0 + a1) / 2 - 0.01, (a0 + a1) / 2 + 0.01)
                v.geom(g, fc="k", ec="k", lw="fine", z=3)
        else:
            sw, hinge = S.DOOR_SWING[o["id"]]
            g = band(b, side, S.WALL, S.WALL, a0, a1)
            x0, y0, x1, y1 = g.bounds
            draw_door(v, side in "SN", (x0, y0, x1, y1), a0, a1, +1 if side in "SW" else -1, hinge)
            g = band(b, side, 0, 0, a0, a1)
            gx0, gy0, gx1, gy1 = g.bounds
            v.line([(gx0, gy0), (gx1, gy1)], lw="thin")
        # 창호 기호
        g = band(b, side, -0.36, -0.36, (a0 + a1) / 2, (a0 + a1) / 2)
        cx, cy = g.bounds[0], g.bounds[1]
        x, y = v.P(cx, cy)
        v.ax.add_patch(MPoly([(x - 3.6, y - 1.8), (x + 3.6, y - 1.8), (x + 3.6, y + 1.8), (x - 3.6, y + 1.8)],
                             closed=True, fc="white", ec="k", lw=LW["thin"] * PT, zorder=6))
        v.ax.text(x, y, o["id"], fontsize=fs(1.8), ha="center", va="center", zorder=7)


def draw_door(v, horizontal, face_box, a0, a1, s, hinge):
    """horizontal: 벽이 x 방향. face_box: 문짝이 붙는 벽면(선). s: 열림 방향(+1: 좌표 증가 쪽)."""
    w = a1 - a0
    x0, y0, x1, y1 = face_box
    if horizontal:
        fy = y0
        hx = a0 if hinge == "lo" else a1
        tip = (hx, fy + s * w)
        v.line([(hx, fy), tip], lw="vis", z=4)
        t_leaf = 90 if s > 0 else 270
        t_closed = 0 if hinge == "lo" else 180
        c = (hx, fy)
    else:
        fx = x0
        hy = a0 if hinge == "lo" else a1
        tip = (fx + s * w, hy)
        v.line([(fx, hy), tip], lw="vis", z=4)
        t_leaf = 0 if s > 0 else 180
        t_closed = 90 if hinge == "lo" else 270
        c = (fx, hy)
    t1, t2 = (t_leaf, t_closed) if (t_closed - t_leaf) % 360 == 90 else (t_closed, t_leaf)
    v.arc(c[0], c[1], w, t1, t2, lw="fine")


def plan_partitions(v, floor):
    for p in S.parts(floor):
        x0, y0, x1, y1 = p["rect"]
        along_y = (y1 - y0) > (x1 - x0)
        lo, hi = (y0, y1) if along_y else (x0, x1)
        cuts = [(d[0], d[1]) for d in p["doors"]]
        segs = [sbox(x0, a, x1, c) if along_y else sbox(a, y0, c, y1) for a, c in iv_sub(lo, hi, cuts)]
        g = unary_union(segs)
        v.geom(g, fc=PART_FC, ec="#888888", lw=0, hatch="xx", z=2)
        v.geom(g, fc="none", ec="k", lw="heavy", z=2.5)
        for a0, a1, sw, hinge, kind, did in p["doors"]:
            if kind != "door":
                continue
            if along_y:
                face = x1 if sw > 0 else x0
                draw_door(v, False, (face, a0, face, a1), a0, a1, sw, hinge)
                tx, ty = face + sw * 0.25, (a0 + a1) / 2
            else:
                face = y1 if sw > 0 else y0
                draw_door(v, True, (a0, face, a1, face), a0, a1, sw, hinge)
                tx, ty = (a0 + a1) / 2, face + sw * 0.25
            v.text(tx, ty, did, 1.5, color="#333333", bg="white")


def plan_stair(v, floor):
    x0, y0, x1, y1 = S.STAIR
    f1 = (x1 - S.STAIR_W, x1)
    f2 = (x0, x0 + S.STAIR_W)
    land = S.LANDING_Y
    if floor == 1:
        brk = y0 + 6 * S.TREAD + 0.1
        for i in range(S.N1):
            y = y0 + i * S.TREAD
            v.line([(f1[0], y), (f1[1], y)], lw="thin" if y < brk else "fine", ls="-" if y < brk else "--")
        v.line([(f1[0], y0), (f1[0], land)], lw="vis")
        v.line([(f1[0] - 0.05, brk - 0.25), (f1[1] + 0.05, brk + 0.25)], lw="vis")
        for i in range(S.RISERS - S.N1):
            y = land - i * S.TREAD
            v.line([(f2[0], y), (f2[1], y)], lw="fine", ls="--")
        v.rect(x0, land, x1, y1, ec="k", lw="fine", ls="--")
        v.rect(f2[0], S.TOP_Y, f2[1], land, ec="#666666", lw="fine", ls="--", hatch="//", fc="none")
        v.text((f2[0] + f2[1]) / 2, y0 + 0.9, "계단하부\n수납", 1.7, color="#444444")
        u = (f1[0] + f1[1]) / 2
        v.line([(u, y0 + 0.15), (u, brk - 0.3)], lw="thin")
        v.ax.annotate("", xy=v.P(u, brk - 0.2), xytext=v.P(u, brk - 0.6),
                      arrowprops=dict(arrowstyle="-|>", lw=LW["thin"] * PT, color="k"))
        v.text(u, y0 + 0.35, "UP", 1.8, bg="white")
    else:
        for i in range(S.N1):
            y = y0 + i * S.TREAD
            v.line([(f1[0], y), (f1[1], y)], lw="thin")
        for i in range(S.RISERS - S.N1):
            y = land - i * S.TREAD
            v.line([(f2[0], y), (f2[1], y)], lw="thin")
        v.line([(x0, land), (x1, land)], lw="thin")
        v.line([(f1[0], y0), (f1[0], land)], lw="thin")
        v.line([(f2[1], S.TOP_Y), (f2[1], land)], lw="thin")
        for (ax_, ay), (bx, by) in S.RAILS_2F:
            v.line([(ax_, ay), (bx, by)], lw="heavy")
        u2, u1 = (f2[0] + f2[1]) / 2, (f1[0] + f1[1]) / 2
        v.line([(u2, S.TOP_Y + 0.1), (u2, land + 0.5), (u1, land + 0.5), (u1, y0 + 0.4)], lw="thin")
        v.ax.annotate("", xy=v.P(u1, y0 + 0.25), xytext=v.P(u1, y0 + 0.65),
                      arrowprops=dict(arrowstyle="-|>", lw=LW["thin"] * PT, color="k"))
        v.text(u2, S.TOP_Y - 0.2, "DN", 1.8, bg="white")
        v.text(u1, y0 + 1.2, "오픈", 1.8, color="#444444", bg="white")
        v.text((x0 + x1) / 2, land + 0.5 + 0.22, "난간 H1,200", 1.4, color="#444444")


def plan_fixtures(v, floor):
    def r(x0, y0, x1, y1, **kw):
        v.rect(x0, y0, x1, y1, ec="#333333", lw="fine", **kw)

    def wc(x, y, rot):                      # 양변기: rot = 물탱크 쪽 방향 ('N','S','E','W')
        if rot in "NS":
            d = 1 if rot == "N" else -1
            r(x - 0.22, y + d * 0.2, x + 0.22, y + d * 0.38)
            v.ax.add_patch(matplotlib.patches.Ellipse(v.P(x, y - d * 0.05), 0.38 * v.k, 0.5 * v.k, fc="none",
                                                      ec="#333333", lw=LW["fine"] * PT, zorder=3))
        else:
            d = 1 if rot == "E" else -1
            r(x + d * 0.2, y - 0.22, x + d * 0.38, y + 0.22)
            v.ax.add_patch(matplotlib.patches.Ellipse(v.P(x - d * 0.05, y), 0.5 * v.k, 0.38 * v.k, fc="none",
                                                      ec="#333333", lw=LW["fine"] * PT, zorder=3))

    def lav(x, y, horiz=True):
        if horiz:
            r(x - 0.3, y - 0.22, x + 0.3, y + 0.22)
        else:
            r(x - 0.22, y - 0.3, x + 0.22, y + 0.3)
        v.ax.add_patch(matplotlib.patches.Ellipse(v.P(x, y), 0.34 * v.k, 0.26 * v.k, fc="none",
                                                  ec="#333333", lw=LW["fine"] * PT, zorder=3))

    def shower(x0, y0, x1, y1):
        r(x0, y0, x1, y1)
        v.line([(x0, y0), (x1, y1)], lw="fine", color="#666666")
        v.line([(x0, y1), (x1, y0)], lw="fine", color="#666666")

    if floor == 1:
        r(1.8, 16.1, 6.0, 16.7)                             # 주방 싱크대
        v.ax.add_patch(Circle(v.P(4.2, 16.4), 0.2 * v.k, fc="none", ec="#333333", lw=LW["fine"] * PT, zorder=3))
        for cx in (2.3, 2.75):
            v.ax.add_patch(Circle(v.P(cx, 16.4), 0.12 * v.k, fc="none", ec="#333333", lw=LW["fine"] * PT, zorder=3))
        r(6.6, 15.9, 7.45, 16.7)                            # 냉장고
        v.line([(6.6, 15.9), (7.45, 16.7)], lw="fine", color="#666666")
        v.text(7.0, 15.75, "냉장고", 1.3, color="#555555")
        r(3.6, 14.2, 5.6, 15.1, ls="--")                    # 식탁
        r(2.2, 9.6, 4.6, 10.5, ls="--")                     # 소파
        r(5.4, 12.6, 7.3, 12.95, ls="--")                   # TV장
        wc(9.55, 10.6, "E")
        lav(8.4, 11.2)
        shower(7.7, 9.35, 8.6, 10.25)
        r(7.7, 16.1, 9.9, 16.65)                            # 다용도: 세탁기·건조기
        v.text(8.8, 15.85, "세탁·건조기", 1.3, color="#555555")
        r(10.15, 9.35, 10.6, 11.0, ls="--")                 # 신발장
        v.text(10.38, 10.2, "신발장", 1.2, color="#555555", rot=90)
    else:
        r(4.0, 9.6, 5.6, 11.7, ls="--")                     # 침대 (Q)
        r(10.9, 9.5, 12.0, 11.5, ls="--")                   # 침대 (S)
        r(7.8, 9.4, 8.9, 10.0, ls="--")                     # 책상
        for y in (14.3, 14.9, 15.5, 16.1):
            v.line([(3.85, y), (4.45, y)], lw="fine", color="#777777")
        r(3.85, 13.8, 4.45, 16.65, ls="--")
        r(4.9, 13.8, 5.45, 16.65, ls="--")
        wc(7.05, 16.2, "N")
        lav(6.25, 16.4)
        shower(5.7, 13.8, 6.8, 14.75)
        v.text(6.25, 15.2, "욕조 대신\n샤워부스", 1.2, color="#555555")


def plan_rooms(v, floor, fl):
    for r_ in S.ROOMS:
        if r_["floor"] != floor:
            continue
        x0, y0, x1, y1 = r_["rects"][0]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if r_["name"] == "계단실":
            continue
        if r_["name"] == "홀" and floor == 2:
            cx, cy = 8.8, 13.9
        if r_["name"] == "홀" and floor == 1:
            cx, cy = 9.0, 12.7
        if r_["name"] == "거실":
            cy = 11.6
        if r_["name"] == "주방·식당":
            cy = 13.6
        v.text(cx, cy + 0.18, r_["name"], 2.6, weight="bold", bg="white")
        v.text(cx, cy - 0.22, f"{S.room_area(r_):.2f}㎡", 1.8, bg="white")
        if r_["name"] != "테라스":
            v.text(cx, cy - 0.5, f"CH {mm(S.CEIL_H)}", 1.4, color="#555555", bg="white")


def grid_lines(v, xr, yr, gx=S.GRID_X, gy=S.GRID_Y, both=True):
    """xr: (u_min, u_max) 그리드 선이 뻗는 범위의 끝 (버블 위치)."""
    for name, x in gx:
        v.line([(x, yr[0]), (x, yr[1])], lw="fine", ls=(0, (12, 3, 2, 3)), color="#555555", z=1)
        v.bubble(x, yr[0] - 0.18, name)
        if both:
            v.bubble(x, yr[1] + 0.18, name)
    for name, y in gy:
        v.line([(xr[0], y), (xr[1], y)], lw="fine", ls=(0, (12, 3, 2, 3)), color="#555555", z=1)
        v.bubble(xr[0] - 0.18, y, name)
        if both:
            v.bubble(xr[1] + 0.18, y, name)


def section_marks(v, floor):
    """A-A: y = SEC_A_Y (북쪽을 봄), B-B: x = SEC_B_X (서쪽을 봄)."""
    ya = SEC_A_Y
    for u, d in ((S.B1[0] - 2.6, 1), (S.B1[2] + 2.0, -1)):
        v.line([(u, ya), (u + d * 0.5, ya)], lw="heavy")
        v.bubble(u, ya - 0.3, "A", r=2.8)
        v.ax.annotate("", xy=v.P(u, ya + 0.7), xytext=v.P(u, ya + 0.02),
                      arrowprops=dict(arrowstyle="-|>", lw=LW["vis"] * PT, color="k"))
    v.line([(S.B1[0] - 2.1, ya), (S.B1[2] + 1.5, ya)], lw="fine", ls=(0, (14, 3, 2, 3)))
    xb = SEC_B_X
    for w, d in ((S.B1[1] - 2.6, 1), (S.B1[3] + 2.0, -1)):
        v.line([(xb, w), (xb, w + d * 0.5)], lw="heavy")
        v.bubble(xb + 0.3, w, "B", r=2.8)
        v.ax.annotate("", xy=v.P(xb - 0.7, w), xytext=v.P(xb - 0.02, w),
                      arrowprops=dict(arrowstyle="-|>", lw=LW["vis"] * PT, color="k"))
    v.line([(xb, S.B1[1] - 2.1), (xb, S.B1[3] + 1.5)], lw="fine", ls=(0, (14, 3, 2, 3)))


SEC_A_Y = 11.0
SEC_B_X = 11.65


PLAN_O = (102, 125)                                    # 1/50 평면의 남서 모서리 (1.5, 9.0) 위치


def plan_notes(sh, notes, y=330):
    sh.text(440, y + 9, "일반 사항", 2.8, weight="bold")
    for n_ in notes:
        sh.text(440, y, n_, 1.9)
        y -= 5.5
    return y


def plan_legend(sh, y=240):
    sh.text(440, y + 9, "범례", 2.8, weight="bold")
    for i, (fc, hatch, s_) in enumerate([(RC_FC, "////", "철근콘크리트 (RC)"), (INS_FC, "....", "외단열 (PF보드)"),
                                         (PART_FC, "xx", "경량 칸막이")]):
        yy = y - i * 7
        sh.ax.add_patch(MPoly([(440, yy - 2), (452, yy - 2), (452, yy + 2), (440, yy + 2)], closed=True,
                              fc=fc, ec="k", hatch=hatch, lw=LW["thin"] * PT, zorder=7))
        sh.text(456, yy, s_, 2.1)



def plan_draw(sh, floor, o=PLAN_O):
    v = sh.view(*o, 50, u0=1.5, v0=9.0)
    fl = S.FL1 if floor == 1 else S.FL2
    b = S.B1 if floor == 1 else S.B2
    x0, y0, x1, y1 = S.B1
    grid_lines(v, (x0 - 2.9, x1 + 2.3), (y0 - 2.9, y1 + 2.3))
    plan_walls(v, b, floor, fl)
    if floor == 2:                                     # 테라스 파라펫 (절단)
        tx0, ty0, tx1, ty1 = S.TERRACE
        para = unary_union([sbox(tx0, ty0, tx0 + 0.15, ty1), sbox(tx0, ty0, tx1, ty0 + 0.15), sbox(tx0, ty1 - 0.15, tx1, ty1)])
        v.solid(para)
        v.rect(tx0 + 0.15, ty0 + 0.15, tx1, ty1 - 0.15, fc="#f4ece0", ec="none", hatch="---", z=1)
        v.text(2.5, 9.7, "합성목재 데크\n(우레탄 도막방수)", 1.6, color="#444444", bg="white")
        v.ax.add_patch(Circle(v.P(1.85, 16.6), 0.1 * v.k, fc="white", ec="k", lw=LW["thin"] * PT, zorder=4))
        v.text(1.85, 16.3, "RD", 1.4)
        v.text(2.9, 15.6, "구배 1/100 → RD", 1.4, color="#444444", rot=90)
    plan_partitions(v, floor)
    plan_stair(v, floor)
    plan_fixtures(v, floor)
    plan_rooms(v, floor, fl)
    section_marks(v, floor)
    ops = S.openings(floor)
    two = [S.B2[0]] if floor == 2 else []

    def pts(wall):
        return [p for o in ops if o["wall"] == wall for p in (o["a0"], o["a1"])]
    v.hdim([x0, x1] + two + pts("S"), y0 - 0.8, ext=y0)
    v.hdim([g for _, g in S.GRID_X], y0 - 1.4)
    v.hdim([x0, x1], y0 - 2.0)
    v.hdim([x0, x1] + two + pts("N"), y1 + 0.8, ext=y1)
    v.hdim([x0, x1], y1 + 1.4)
    v.vdim([y0, y1] + pts("W"), x0 - 0.8, ext=x0)
    v.vdim([g for _, g in S.GRID_Y], x0 - 1.4)
    v.vdim([y0, y1], x0 - 2.0)
    v.vdim([y0, y1] + pts("E"), x1 + 0.8, ext=x1)
    v.vdim([y0, y1], x1 + 1.4)
    if floor == 1:
        v.hdim([1.8, 7.5, 7.65, 9.95, 10.1, 12.2], 14.65, size=1.6)
    else:
        v.hdim([3.8, 5.5, 5.65, 7.5, 7.65, 9.95, 10.1, 12.2], 15.35, size=1.6)
    return v


def plan_sheet(book, floor):
    no = f"A-20{floor}"
    sh = Sheet(book, no, f"{floor}층 평면도", "1/50")
    v = plan_draw(sh, floor)
    lev = "1FL : GL+300" if floor == 1 else "2FL : GL+3,300"
    sh.heading(20, 398, f"{floor}층 평면도", "1/50", num=str(floor))
    sh.text(30, 384, f"바닥 레벨 {lev}   |   바닥면적 {(S.AREA_1F if floor == 1 else S.AREA_2F):.2f}㎡ (외벽 중심선)", 2.2)
    sh.north(560, 380)
    notes = [
        "1. 외벽: 스터코 10 + PF보드(준불연) 100 + RC 180 + 석고보드 9.5 (총 300)",
        "2. 내벽: 경량철골 칸막이 + 석고보드 9.5 2겹 양면 (THK150)",
        "    욕실·다용도실은 방수석고보드",
        "3. 창호 기호 W·D: A-001 창호일람표, AD: 내부 문",
        "4. 절단 높이 FL+1,200 위의 창은 점선",
        "5. 단면 표시 A-A' (A-401), B-B' (A-402)",
        "6. 치수: 외벽 바깥면·그리드(벽 중심선) 기준, 단위 mm",
    ]
    if floor == 2:
        notes += ["7. 계단 오픈부 둘레 난간 H1,200 (강관 + 강화유리)",
                  "8. 테라스: 우레탄 도막방수, RD 루프드레인 Ø100,",
                  "    파라펫 H1,200, 데크 마감 +3,250 (2FL -50)"]
    else:
        notes += ["7. 현관 바닥 FL-30 (턱), 화장실 FL-20 (구배 1/100)",
                  "8. 계단 하부 수납장 (점검구 600x600)"]
    plan_notes(sh, notes)
    plan_legend(sh)
    sh.save()


# ---------------------------------------------------------------- 지붕 평면도
def roof_draw(sh, o=PLAN_O):
    v = sh.view(*o, 50, u0=1.5, v0=9.0)
    x0, y0, x1, y1 = S.B2
    ex0, ex1, ey0, ey1 = x0 - S.EAVE, x1 + S.EAVE, y0 - S.EAVE, y1 + S.EAVE
    grid_lines(v, (S.B1[0] - 2.9, S.B1[2] + 2.3), (S.B1[1] - 2.9, S.B1[3] + 2.3))
    v.rect(ex0, ey0, ex1, ey1, fc="#e8e8e8", ec="k", lw="cut", hatch="---", z=2)
    v.line([(ex0, S.RIDGE_Y), (ex1, S.RIDGE_Y)], lw="cut", z=3)
    v.rect(x0, y0, x1, y1, ec="k", lw="thin", ls="--", z=3)
    for yy in (ey0 - 0.12, ey1 + 0.12):
        v.rect(ex0, yy - 0.06, ex1, yy + 0.06, fc="white", ec="k", lw="thin", z=3)
    for xx, yy in ((ex0 + 0.15, ey0 - 0.12), (ex1 - 0.15, ey0 - 0.12), (ex0 + 0.15, ey1 + 0.12), (ex1 - 0.15, ey1 + 0.12)):
        v.ax.add_patch(Circle(v.P(xx, yy), 0.06 * v.k, fc="white", ec="k", lw=LW["thin"] * PT, zorder=4))
    for xx in (5.0, 8.0, 11.0):
        for ya, yb in ((S.RIDGE_Y - 0.6, ey0 + 0.6), (S.RIDGE_Y + 0.6, ey1 - 0.6)):
            v.ax.annotate("", xy=v.P(xx, yb), xytext=v.P(xx, ya),
                          arrowprops=dict(arrowstyle="-|>", lw=LW["thin"] * PT, color="k"))
        v.text(xx + 0.2, (S.RIDGE_Y + ey0) / 2, "물매 5/10", 1.9, rot=90, bg="#e8e8e8")
        v.text(xx + 0.2, (S.RIDGE_Y + ey1) / 2, "물매 5/10", 1.9, rot=90, bg="#e8e8e8")
    v.text((ex0 + ex1) / 2, S.RIDGE_Y + 0.25, "용마루 (용마루 캡 + 환기 벤트)", 1.9, bg="#e8e8e8")
    v.text((ex0 + ex1) / 2, ey0 - 0.42, "알루미늄 처마홈통 W150 / 선홈통 Ø100 (4개소)", 1.8)
    tx0, ty0, tx1, ty1 = S.TERRACE
    para = unary_union([sbox(tx0, ty0, tx0 + 0.15, ty1), sbox(tx0, ty0, tx1, ty0 + 0.15), sbox(tx0, ty1 - 0.15, tx1, ty1)])
    v.solid(para)
    v.rect(tx0 + 0.15, ty0 + 0.15, ex0, ty1 - 0.15, fc="#f4ece0", ec="none", hatch="---", z=1)
    v.ax.add_patch(Circle(v.P(1.85, 16.6), 0.1 * v.k, fc="white", ec="k", lw=LW["thin"] * PT, zorder=4))
    v.text(1.85, 16.3, "RD", 1.4)
    v.text(2.25, 13.0, "테라스\nFL+3,250\n우레탄 도막방수\n+ 합성목재 데크", 1.7, bg="#f4ece0")
    v.hdim([ex0, x0, x1, ex1], ey0 - 0.9, ext=ey0)
    v.hdim([tx0, ex1], ey0 - 1.5)
    v.vdim([ey0, y0, y1, ey1], tx0 - 0.8, ext=ex0)
    v.vdim([ey0, ey1], tx0 - 1.4)
    return v


def roof_sheet(book):
    sh = Sheet(book, "A-203", "지붕 평면도", "1/50")
    v = roof_draw(sh)
    sh.heading(20, 398, "지붕 평면도", "1/50", num="3")
    sh.north(560, 380)
    plan_notes(sh, ["1. 지붕: 아스팔트 싱글 / 자착식 방수시트 / OSB 11 / 통기층 30",
                    "    / PF보드 160 / RC 150",
                    "2. 처마 하부 펀칭 소핏 → 용마루 벤트로 통기",
                    "3. 처마홈통·선홈통: 알루미늄 도장, 선홈통은 우수 맨홀로 연결",
                    "4. 테라스 RD: 루프드레인 Ø100 + 오버플로 1개소",
                    "5. 박공 끝 (동·서): 알루미늄 후레싱",
                    "6. 처마 내밀기 500 (1 m 미만, 건축면적 불산입)"])
    sh.save()


# ---------------------------------------------------------------- 배치도
def site_draw(sh, o=(110, 120), scale=100):
    v = sh.view(*o, scale)
    L, D = S.LOT_W, S.LOT_D
    v.rect(-4, -S.ROAD_W, L + 4, 0, fc="#e4e4e4", ec="none", z=1)
    v.line([(-4, -S.ROAD_W), (L + 4, -S.ROAD_W)], lw="thin")
    v.line([(-4, -S.ROAD_W / 2), (L + 4, -S.ROAD_W / 2)], lw="fine", ls=(0, (10, 4)))
    v.text(L / 2, -S.ROAD_W / 2 - 0.9, f"도로 (폭 {mm(S.ROAD_W)})", 2.6)
    for xs, ys, xe, ye in ((-4, 0, 0, 0), (L, 0, L + 4, 0), (-4, 0, -4, D + 2), (L + 4, 0, L + 4, D + 2)):
        v.line([(xs, ys), (xe, ye)], lw="fine", ls=":", color="#777777")
    v.text(-3.0, D / 2, "인접 대지 (단독주택용지)", 2.0, color="#555555", rot=90)
    v.text(L + 3.0, D / 2, "인접 대지 (단독주택용지)", 2.0, color="#555555", rot=90)
    v.text(L / 2, D + 1.2, "인접 대지 (단독주택용지)", 2.0, color="#555555")
    v.rect(*S.GARDEN, fc="#dff0d0", ec="#3d7a2a", lw="thin", hatch="..", z=1)
    v.rect(*S.NORTH_GARDEN, fc="#dff0d0", ec="#3d7a2a", lw="thin", hatch="..", z=1)
    v.rect(9.1, 0, L - 0.05, 8.9, fc="#efefef", ec="k", lw="thin", z=1)
    for hx0, hy0, hx1, hy1 in ((0, 0, S.HEDGE_T, D), (0, D - S.HEDGE_T, L, D), (L - S.HEDGE_T, 9.0, L, D)):
        v.rect(hx0, hy0, hx1, hy1, fc="#bcd9a8", ec="#3d7a2a", lw="fine", z=1.5)
    for i, (px, py) in enumerate(S.PARKING, 1):
        v.rect(px, py, px + S.PARK_W, py + S.PARK_D, ec="k", lw="thin", z=2)
        v.text(px + S.PARK_W / 2, py + S.PARK_D / 2, f"주차 {i}\n2,500 x 5,000", 1.9)
    for x, y, h in [(1.6, 1.6, 4.0), (5.0, 1.4, 3.2), (1.4, 6.5, 3.6), (12.6, 18.4, 4.2), (3.0, 18.6, 3.8)]:
        v.ax.add_patch(Circle(v.P(x, y), h * 0.28 * v.k, fc="none", ec="#3d7a2a", lw=LW["thin"] * PT, zorder=3))
    x0, y0, x1, y1 = S.B1
    v.rect(x0, y0, x1, y1, fc="#cccccc", ec="k", lw="cut", hatch="////", z=3)
    v.rect(x0, y0, S.TERRACE[2], y1, fc="#e8e0d0", ec="k", lw="vis", z=3.2)
    v.rect(S.B2[0] - S.EAVE, y0 - S.EAVE, S.B2[2] + S.EAVE, y1 + S.EAVE, ec="k", lw="thin", ls="--", z=3.4)
    v.text((S.B2[0] + x1) / 2, 13.4, "주택 (지상 2층)", 3.0, weight="bold", bg="#cccccc")
    v.text((S.B2[0] + x1) / 2, 12.5, f"1FL GL+300  /  최고높이 {mm(S.Z_TOP)}", 2.0, bg="#cccccc")
    v.text(2.5, 13.0, "2층\n테라스", 2.0, bg="#e8e0d0")
    v.text((S.B2[0] + x1) / 2, y0 - 0.25, "지붕 처마선 (점선)", 1.5, bg="#efefef")
    v.poly([(0, 0), (L, 0), (L, D), (0, D)], ec="#c00000", lw="heavy", ls=(0, (14, 3, 2, 3)), z=5)
    v.text(4.0, 0.3, "대지경계선 (= 도로경계선)", 1.7, color="#c00000")
    v.line([(0, D - 1.5), (L, D - 1.5)], lw="thin", ls="--", color="#0050a0", z=5)
    v.text(L - 0.8, D - 1.5 + 0.3, "정북일조 이격선 (높이 10m 이하: 1.5m)", 1.7, color="#0050a0", ha="right", bg="#dff0d0")
    v.hdim([0, x0, x1, L], -0.9, ext=None)
    v.hdim([0, L], -S.ROAD_W - 1.0)
    v.vdim([0, y0, y1, D], -1.2)
    v.vdim([0, D], -2.0)
    v.ax.annotate("", xy=v.P(11.8, 0.6), xytext=v.P(11.8, -2.0),
                  arrowprops=dict(arrowstyle="-|>", lw=LW["vis"] * PT, color="k"))
    v.text(11.8, -2.4, "차량 출입", 1.9)
    v.ax.annotate("", xy=v.P(11.4, 8.8), xytext=v.P(9.6, 0.2),
                  arrowprops=dict(arrowstyle="-|>", lw=LW["thin"] * PT, color="k", ls="--"))
    v.text(9.4, -2.4, "보행 출입", 1.9)
    v.line([(8.7, 9.0), (8.7, -1.0)], lw="thin", ls=(0, (6, 2, 1, 2)), color="#7a3d00", z=4)
    v.text(8.45, 4.6, "오수관 PVC Ø150 (구배 1/50)", 1.5, color="#7a3d00", rot=90)
    v.rect(8.45, -1.5, 8.95, -1.0, fc="white", ec="#7a3d00", lw="thin", z=4)
    v.text(8.7, -1.85, "오수 맨홀", 1.4, color="#7a3d00")
    v.line([(13.0, 8.4), (13.0, 1.0), (14.0, 0.4)], lw="thin", ls=(0, (2, 2)), color="#0050a0", z=4)
    v.line([(0.9, 9.0), (0.9, 0.4)], lw="thin", ls=(0, (2, 2)), color="#0050a0", z=4)
    v.text(1.15, 4.6, "우수관 PE Ø150", 1.5, color="#0050a0", rot=90)
    for xx, yy in ((14.0, 0.25), (0.9, 0.25)):
        v.rect(xx - 0.2, yy - 0.2, xx + 0.2, yy + 0.2, fc="white", ec="#0050a0", lw="thin", z=4)
    v.text(4.7, 7.7, f"조경 {(S.GARDEN[2] - S.GARDEN[0]) * (S.GARDEN[3] - S.GARDEN[1]):.2f}㎡", 2.0, bg="#dff0d0")
    v.text(5.0, 17.85, f"조경 {(S.NORTH_GARDEN[2] - S.NORTH_GARDEN[0]) * (S.NORTH_GARDEN[3] - S.NORTH_GARDEN[1]):.2f}㎡",
           2.0, bg="#dff0d0")
    v.text(0.3, 12.0, "생울타리 H1,200", 1.6, rot=90, color="#3d7a2a")
    return v


def site_sheet(book):
    sh = Sheet(book, "A-101", "배치도", "1/100")
    v = site_draw(sh)
    sh.heading(20, 398, "배치도", "1/100")
    sh.north(330, 380)
    rows = [("항목", "내용"),
            ("대지위치", "경상북도 경산시 진량읍 신제리·다문리 일원"),
            ("", "경산4일반산업단지 단독주택용지 (필지번호 미정)"),
            ("지역·지구", "제1종일반주거지역, 지구단위계획구역"),
            ("대지면적", f"{S.LOT_AREA:.2f}㎡  ({mm(S.LOT_W)} x {mm(S.LOT_D)})"),
            ("건축면적", f"{S.BUILDING_AREA:.2f}㎡  (건폐율 {S.BUILDING_AREA / S.LOT_AREA:.2%} / 60%)"),
            ("연면적", f"{S.GFA:.2f}㎡  (용적률 {S.GFA / S.LOT_AREA:.2%} / 180%)"),
            ("규모·높이", f"지상 2층, 최고높이 {S.Z_TOP:.2f}m"),
            ("주차", f"{len(S.PARKING)}대 (법정 1대), 일반형 2.5 x 5.0 m"),
            ("조경", f"{S.LANDSCAPE:.2f}㎡ ({S.LANDSCAPE / S.LOT_AREA:.1%})"),
            ("이격거리", f"정북 {S.LOT_D - S.B1[3]:.1f}m, 서 {S.B1[0]:.1f}m, 동 {S.LOT_W - S.B1[2]:.1f}m, 남 {S.B1[1]:.1f}m")]
    y = sh.table(370, 360, [32, 172], rows, rh=7.0, size=2.1)
    for i, s_ in enumerate(["※ 필지 확정 후 지적측량 성과도로 대지 형상·면적·도로 폭을 다시 확인합니다.",
                            "※ 오수: 분류식 공공하수관 직접 연결 (정화조 없음, 지구 하수계획 확인).",
                            "※ 설계 지반고 GL±0 = 도로 경계 보도 상단 +150 (현황측량 후 확정).",
                            "※ 우수: 선홈통 → 우수관 → 도로측 우수 맨홀 (빗물 침투 화단 병행 검토)."]):
        sh.text(370, y - 10 - i * 6, s_, 1.9)
    sh.save()


# ---------------------------------------------------------------- 입면도
def window_elev(v, u0, u1, z0, z1, kind, mirror=False):
    a, b = min(u0, u1), max(u0, u1)
    if kind == "door":
        v.rect(a, z0, b, z1, fc="#f2ede6", ec="k", lw="vis", z=5)
        v.rect(a + 0.06, z0, b - 0.06, z1 - 0.06, ec="k", lw="fine", z=5)
        v.rect(a + 0.2, z0 + 0.3, b - 0.2, z1 - 0.3, fc="#dcebf5", ec="k", lw="fine", z=5)
        if z1 - z0 > 1.5:
            v.ax.add_patch(Circle(v.P(b - 0.13, z0 + 1.05), 0.6, fc="k", zorder=6))
        return
    v.rect(a, z0, b, z1, fc="#dcebf5", ec="k", lw="vis", z=5)
    v.rect(a + 0.05, z0 + 0.05, b - 0.05, z1 - 0.05, ec="k", lw="fine", z=5)
    n = 1 if b - a < 1.3 else (2 if b - a < 3.2 else 3)
    for i in range(1, n):
        u = a + (b - a) * i / n
        v.line([(u, z0 + 0.05), (u, z1 - 0.05)], lw="thin", z=5)
    v.rect(a - 0.05, z0 - 0.04, b + 0.05, z0, fc="white", ec="k", lw="thin", z=5)
    v.line([(a + 0.2, z0 + 0.2), (a + 0.6, z1 - 0.3)], lw="fine", color="#8aa8bf", z=5)


def elev_wall(v, U, a0, a1, z0, z1, ops, wall, floor_band=True, top=None):
    """U: 벽 방향 좌표 -> 도면 u. top: (u, z) 꼭짓점 목록이면 박공."""
    pts = [(U(a0), z0), (U(a1), z0)]
    if top:
        pts += [(U(a1), z1)] + [(U(a), z) for a, z in top] + [(U(a0), z1)]
    else:
        pts += [(U(a1), z1), (U(a0), z1)]
    v.poly(pts, fc="white", ec="k", lw="heavy", z=3)
    for o in ops:
        if o["wall"] == wall:
            window_elev(v, U(o["a0"]), U(o["a1"]), o["z0"], o["z1"], o["kind"])


def roof_front(v, U, z_from_eave=True):
    """남·북 입면에서 보이는 지붕면."""
    ex0, ex1 = S.B2[0] - S.EAVE, S.B2[2] + S.EAVE
    a, b = sorted((U(ex0), U(ex1)))
    v.rect(a, S.Z_EAVE + S.ROOF_T, b, S.Z_TOP, fc="#6e7178", ec="k", lw="heavy", hatch="---", z=6)
    v.rect(a, S.Z_EAVE, b, S.Z_EAVE + S.ROOF_T, fc="#f0f0f0", ec="k", lw="vis", z=6)
    v.rect(a - 0.02, S.Z_EAVE - 0.08, b + 0.02, S.Z_EAVE + 0.1, fc="#bfc3c8", ec="k", lw="thin", z=6.2)
    v.line([(a, S.Z_TOP), (b, S.Z_TOP)], lw="cut", z=6.3)


def roof_verge(v, U):
    """동·서 입면의 박공 지붕 끝 (단면 모양)."""
    ey0, ey1 = S.B2[1] - S.EAVE, S.B2[3] + S.EAVE
    zr = S.Z_EAVE + (S.RIDGE_Y - ey0) * S.ROOF_PITCH
    pts = [(U(ey0), S.Z_EAVE), (U(S.RIDGE_Y), zr), (U(ey1), S.Z_EAVE), (U(ey1), S.Z_EAVE + S.ROOF_T),
           (U(S.RIDGE_Y), zr + S.ROOF_T), (U(ey0), S.Z_EAVE + S.ROOF_T)]
    v.poly(pts, fc="#6e7178", ec="k", lw="heavy", z=6)
    for yy in (ey0, ey1):
        v.rect(U(yy) - 0.1, S.Z_EAVE - 0.08, U(yy) + 0.1, S.Z_EAVE + 0.1, fc="#bfc3c8", ec="k", lw="thin", z=6.2)


def elev_common(v, umin, umax, right_u, label_side="right"):
    v.line([(umin - 1.0, 0), (umax + 1.0, 0)], lw=0.7, z=7)
    v.rect(umin - 1.0, -0.5, umax + 1.0, 0, fc="none", ec="none", hatch="\\\\\\", z=1)
    for z, lab in ((S.Z_TOP, f"최고높이 +{mm(S.Z_TOP)}"), (S.TOP2, f"처마 +{mm(S.TOP2)}"),
                   (S.FL2, f"2FL +{mm(S.FL2)}"), (S.FL1, f"1FL +{mm(S.FL1)}"), (0, "GL ±0")):
        v.level(right_u, z, lab, side=label_side, length=20)


def elevation(sh, v, which):
    x0, y0, x1, y1 = S.B1
    if which in ("S", "N"):
        U = (lambda x: x) if which == "S" else (lambda x: S.LOT_W - x)
        ops1 = [o for o in S.openings(1)]
        ops2 = [o for o in S.openings(2)]
        elev_wall(v, U, x0, x1, 0, S.FL2, ops1, which)
        elev_wall(v, U, S.B2[0], S.B2[2], S.FL2, S.TOP2, ops2, which)
        elev_wall(v, U, x0, S.TERRACE[2], S.FL2, S.FL2 + S.RAIL_H, [], which)
        v.line([(U(x0), S.FL2 - 0.12), (U(x1), S.FL2 - 0.12)], lw="fine", z=4)
        v.line([(U(x0), S.FL2 + S.RAIL_H - 0.06), (U(S.TERRACE[2]), S.FL2 + S.RAIL_H - 0.06)], lw="fine", z=4)
        roof_front(v, U)
        for xx, ztop, zb in ((x1 + 0.08, S.Z_EAVE, 0), (S.B2[0] + 0.08, S.Z_EAVE, S.FL2 + S.RAIL_H), (x0 - 0.08, S.FL2, 0)):
            v.rect(U(xx) - 0.05, zb, U(xx) + 0.05, ztop, fc="#bfc3c8", ec="k", lw="fine", z=6)
        umin, umax = sorted((U(x0 - 0.6), U(x1 + 0.6)))
        v.rect(min(U(x0), U(x1)), S.MAT_TOP - 0.0, max(U(x0), U(x1)), S.FOOT_BOT, ec="#777777", lw="fine", ls="--", z=1)
        elev_common(v, umin, umax, umax + 0.2)
        v.vdim([0, S.FL1, S.FL2, S.TOP2, S.Z_TOP], umin - 0.6, ext=umin + 0.6)
        v.vdim([0, S.Z_TOP], umin - 1.3)
        v.hdim([U(x0), U(S.TERRACE[2]), U(x1)], -1.2, ext=0)
        mid = U((S.B2[0] + x1) / 2)
        return umin, umax, mid
    U = (lambda y: y) if which == "E" else (lambda y: S.LOT_D - y)
    gable = [(S.RIDGE_Y, S.Z_RIDGE_UNDER)]
    if which == "E":
        elev_wall(v, U, y0, y1, 0, S.TOP2, S.openings(1) + S.openings(2), "E", top=gable)
        v.line([(U(y0), S.FL2 - 0.12), (U(y1), S.FL2 - 0.12)], lw="fine", z=4)
        roof_verge(v, U)
    else:
        elev_wall(v, U, y0, y1, S.FL2, S.TOP2, [], "W", top=gable)
        roof_verge(v, U)
        elev_wall(v, U, y0, y1, 0, S.FL2 + S.RAIL_H, S.openings(1), "W")
        for o in S.openings(2):                         # 파라펫 위로 보이는 2층 문·창 윗부분
            if o["wall"] == "W" and o["z1"] > S.FL2 + S.RAIL_H:
                window_elev(v, U(o["a0"]), U(o["a1"]), S.FL2 + S.RAIL_H + 0.06, o["z1"], o["kind"])
        v.line([(U(y0), S.FL2 - 0.12), (U(y1), S.FL2 - 0.12)], lw="fine", z=4)
        v.line([(U(y0), S.FL2 + S.RAIL_H - 0.06), (U(y1), S.FL2 + S.RAIL_H - 0.06)], lw="fine", z=4)
    umin, umax = sorted((U(y0 - 0.6), U(y1 + 0.6)))
    v.rect(min(U(y0), U(y1)), S.MAT_TOP, max(U(y0), U(y1)), S.FOOT_BOT, ec="#777777", lw="fine", ls="--", z=1)
    elev_common(v, umin, umax, umax + 0.2)
    v.vdim([0, S.FL1, S.FL2, S.TOP2, S.Z_TOP], umin - 0.6, ext=umin + 0.6)
    v.vdim([0, S.Z_TOP], umin - 1.3)
    v.hdim([U(y0), U(S.RIDGE_Y), U(y1)], -1.2, ext=0)
    return umin, umax, U(S.RIDGE_Y)


def elev_notes(v, which, tx):
    """마감 지시선: 오른쪽 열에 높이 순으로."""
    if which in ("S", "N"):
        U = (lambda x: x) if which == "S" else (lambda x: S.LOT_W - x)
        rx = 12.0 if which == "S" else 3.9
        items = [((U(rx), 7.9), "아스팔트 싱글 (흑회색)"), ((U(rx), S.Z_EAVE + 0.1), "알루미늄 처마홈통 W150"),
                 ((U(rx + (0.3 if which == "S" else -0.2)), 5.9), "스터코 마감 (준불연, 백색) / 외단열 PF보드 100"),
                 ((U(10.0 if which == "S" else 8.6), S.FL2 + 1.6), "PVC 시스템창호 (24mm 삼중 로이유리)"),
                 ((U(12.0 if which == "S" else 2.5), S.FL2 - 0.12), "층간 줄눈 (스터코 V-줄눈)"),
                 ((U(12.58 if which == "S" else 1.42), 1.5), "선홈통 Ø100 (알루미늄)"),
                 ((U(12.0 if which == "S" else 2.5), 0.15), "걸레받이 화강석 버너구이 THK30, H300")]
    else:
        U = (lambda y: y) if which == "E" else (lambda y: S.LOT_D - y)
        items = [((U(16.0), 7.6), "박공 지붕 끝: 알루미늄 후레싱"), ((U(15.5), 6.9), "박공벽 (RC + 외단열 PF 100)"),
                 ((U(16.5), S.Z_EAVE + 0.1), "알루미늄 처마홈통 W150"),
                 ((U(16.2), 5.0), "스터코 마감 (준불연, 백색)"),
                 ((U(16.2), 0.15), "걸레받이 화강석 버너구이 THK30, H300")]
        if which == "W":
            items.insert(3, ((U(15.5), S.FL2 + S.RAIL_H - 0.05), "테라스 파라펫 H1,200 + 알루미늄 두겁"))
    items.sort(key=lambda it: -it[0][1])
    last = None
    for (u, z), s_ in items:
        ty = v.P(u, z)[1]
        if last is not None and ty > last - 7:
            ty = last - 7
        v.leader(u, z, tx, ty, s_, size=2.0)
        last = ty


def elevation_draw(sh, which, org=(70, 120), scale=50, notes_dx=62):
    if which in "SN":
        umin = 0.9 if which == "S" else S.LOT_W - 13.1
    else:
        umin = 8.4 if which == "E" else S.LOT_D - 17.6
    v = sh.view(*org, scale, u0=umin)
    umin_, umax, _ = elevation(sh, v, which)
    for o in S.OPENINGS:                                 # 창호 기호
        if o["wall"] != which:
            continue
        U = {"S": lambda a: a, "N": lambda a: S.LOT_W - a, "E": lambda a: a, "W": lambda a: S.LOT_D - a}[which]
        u = (U(o["a0"]) + U(o["a1"])) / 2
        if which == "W" and o["floor"] == 2 and o["z0"] < S.FL2 + S.RAIL_H:
            continue
        x, y = v.P(u, o["z0"] - 0.22)
        sh.ax.add_patch(MPoly([(x - 4, y - 1.8), (x + 4, y - 1.8), (x + 4, y + 1.8), (x - 4, y + 1.8)], closed=True,
                              fc="white", ec="k", lw=LW["thin"] * PT, zorder=8))
        sh.text(x, y, o["id"], 1.9, ha="center")
    elev_notes(v, which, v.P(umax, 0)[0] + notes_dx)
    return v


def elevation_sheet(book, no, which):
    names = {"S": "남측 입면도", "N": "북측 입면도", "E": "동측 입면도", "W": "서측 입면도"}
    sh = Sheet(book, no, names[which], "1/50")
    elevation_draw(sh, which)
    sh.heading(20, 398, names[which], "1/50", num={"S": "1", "N": "2", "E": "3", "W": "4"}[which])
    sh.text(440, 140, "외부 마감 사항", 2.8, weight="bold")
    fin = ["외벽: 스터코(준불연) 백색, 하부 걸레받이 화강석 THK30 H300",
           "지붕: 아스팔트 싱글 (흑회색), 처마 하부 알루미늄 소핏",
           "창호: PVC 시스템창호 (회색 래핑), 24mm 삼중 로이유리",
           "홈통: 알루미늄 처마홈통 W150, 선홈통 Ø100",
           "테라스 파라펫: RC + 외단열, 상부 알루미늄 두겁"]
    for j, s_ in enumerate(fin):
        sh.text(440, 131 - j * 6, f"{j + 1}. {s_}", 1.9)
    sh.save()


# ---------------------------------------------------------------- 단면도
def floor_layers(v, u0, u1, z_top, layers, fcs=None):
    z = z_top
    for i, (name, t) in enumerate(layers):
        if t <= 0:
            v.line([(u0, z), (u1, z)], lw="fine", ls="--")
            continue
        fc = "#fff4c2" if ("단열" in name or "PF" in name or "압출" in name) else "#f2f2f2"
        hatch = "...." if fc == "#fff4c2" else None
        v.rect(u0, z - t, u1, z, fc=fc, ec="k", lw="fine", hatch=hatch, z=2)
        z -= t


def earth(v, u0, u1, z0=-1.3):
    v.rect(u0, z0, u1, 0, fc="#f3eee6", ec="none", hatch="\\\\\\", z=0.5)
    v.line([(u0, 0), (u1, 0)], lw=0.7, z=7)


def foundation_section(v, a, b):
    """a..b: 외벽 바깥면 사이 (단면 방향 좌표)."""
    g = unary_union([sbox(a, S.MAT_BOT, b, S.MAT_TOP), sbox(a, S.FOOT_BOT, a + S.FOOT_W, S.MAT_BOT),
                     sbox(b - S.FOOT_W, S.FOOT_BOT, b, S.MAT_BOT)])
    # 버림·잡석
    for (c, d, zb) in ((a, a + S.FOOT_W, S.FOOT_BOT), (b - S.FOOT_W, b, S.FOOT_BOT), (a + S.FOOT_W, b - S.FOOT_W, S.MAT_BOT)):
        v.rect(c, zb - 0.06, d, zb, fc="#cfcfcf", ec="k", lw="fine", z=1.5)
        v.rect(c, zb - 0.26, d, zb - 0.06, fc="#ffffff", ec="k", lw="fine", hatch="oo", z=1.5)
    for c in (a - 0.05, b):
        v.rect(c, S.FOOT_BOT + 0.05, c + 0.05, 0.0, fc=INS_FC, ec="k", lw="fine", hatch="....", z=2)
    return g


def wall_section(lo, hi, z0, z1, outer_at, holes=()):
    """외벽 단면: lo..hi (바깥면 outer_at 쪽에 단열). holes: (z0, z1) 개구부."""
    segs = [(c, d) for c, d in iv_sub(z0, z1, holes)]
    rc, ins = [], []
    for c, d in segs:
        if outer_at == "lo":
            ins.append(sbox(lo, c, lo + O_INS1, d))
            rc.append(sbox(lo + O_RC0, c, hi, d))
        else:
            ins.append(sbox(hi - O_INS1, c, hi, d))
            rc.append(sbox(lo, c, hi - O_RC0, d))
    return rc, ins


def window_section(v, a, b, z0, z1, kind):
    """단면에서 잘린 창: 프레임 + 유리."""
    m = (a + b) / 2
    v.rect(m - 0.035, z0, m + 0.035, z1, fc="#dcebf5", ec="k", lw="thin", z=4)
    v.line([(a, z0), (b, z0)], lw="thin")
    v.line([(a, z1), (b, z1)], lw="thin")
    if kind == "win":
        v.rect(a - 0.04, z0 - 0.03, m, z0, fc="white", ec="k", lw="fine", z=4)


def draw_rc(v, rc_list, ins_list):
    rc_u = unary_union(rc_list)
    ins_u = unary_union(ins_list).difference(rc_u)
    v.geom(rc_u, fc=RC_FC, ec="#555555", lw=0, hatch="////", z=2)
    v.geom(ins_u, fc=INS_FC, ec="#b08a00", lw=0, hatch="....", z=2)
    v.geom(unary_union([rc_u, ins_u]), fc="none", ec="k", lw="cut", z=2.6)
    v.geom(ins_u, fc="none", ec="k", lw="fine", z=2.5)


def roof_section_cross(v, u_of_y):
    """B-B: 용마루에 직각인 지붕 단면 (경사판). u_of_y: y -> u."""
    ey0, ey1 = S.B2[1] - S.EAVE, S.B2[3] + S.EAVE
    zr = S.Z_EAVE + (S.RIDGE_Y - ey0) * S.ROOF_PITCH

    def plate(t0, t1):
        return Polygon([(u_of_y(ey0), S.Z_EAVE + t0), (u_of_y(S.RIDGE_Y), zr + t0), (u_of_y(ey1), S.Z_EAVE + t0),
                        (u_of_y(ey1), S.Z_EAVE + t1), (u_of_y(S.RIDGE_Y), zr + t1), (u_of_y(ey0), S.Z_EAVE + t1)])
    rc = plate(0, S.ROOF_RC)
    ins = plate(S.ROOF_RC, S.ROOF_RC + 0.16)
    top = plate(S.ROOF_RC + 0.16, S.ROOF_T)
    return rc, ins, top


def section_A(sh, o=(80, 125)):
    v = sh.view(*o, 50, u0=0.5, v0=-2.7)
    y = SEC_A_Y
    earth(v, 0.6, 13.4)
    x0, _, x1, _ = S.B1
    rc, ins = [foundation_section(v, x0, x1)], []
    z_s1b = S.FL2 - S.SLAB                       # S1 하단
    z_s1t = z_s1b + S.SLAB_RC
    z_s2b = z_s1b - S.TERRACE_DROP
    z_s2t = z_s2b + S.SLAB_RC
    zr = S.roof_under(y)
    # 서측 외벽 1층 (W5 개구부) + 파라펫
    w5 = [(o["z0"], o["z1"]) for o in S.openings(1) if o["wall"] == "W" and o["a0"] <= y <= o["a1"]]
    r_, i_ = wall_section(x0, x0 + S.WALL, S.MAT_TOP, z_s2b, "lo", w5)
    rc += r_
    ins += i_
    rc.append(sbox(x0 + O_RC0, z_s2b, x0 + O_RC0 + 0.15, S.FL2 + S.RAIL_H))
    ins.append(sbox(x0, z_s2b, x0 + O_INS1, S.FL2 + S.RAIL_H))
    rc.append(sbox(x0, z_s2b, S.TERRACE[2], z_s2t))                        # S2
    rc.append(sbox(S.TERRACE[2], z_s1b, x1, z_s1t))                        # S1
    for bm in S.BEAMS:                                                     # 잘린 보 (y 방향 보)
        if bm["axis"] == "y":
            rc.append(sbox(bm["at"] - bm["b"] / 2, z_s1t - bm["h"], bm["at"] + bm["b"] / 2, z_s1t))
    # 2층 서측 외벽 (D2)
    d2 = [(o["z0"], o["z1"]) for o in S.openings(2) if o["wall"] == "W" and o["a0"] <= y <= o["a1"]]
    r_, i_ = wall_section(S.B2[0], S.B2[0] + S.WALL, z_s1t, zr, "lo", d2)
    rc += r_
    ins += i_
    # 동측 외벽 (1층 + 2층, W13)
    e2 = [(o["z0"], o["z1"]) for o in S.openings(2) + S.openings(1) if o["wall"] == "E" and o["a0"] <= y <= o["a1"]]
    r_, i_ = wall_section(x1 - S.WALL, x1, S.MAT_TOP, zr, "hi", e2)
    rc += r_
    ins += i_
    # 지붕 (용마루와 평행한 절단 -> 수평 띠)
    ex0, ex1 = S.B2[0] - S.EAVE, S.B2[2] + S.EAVE
    rc.append(sbox(ex0, zr, ex1, zr + S.ROOF_RC))
    ins.append(sbox(ex0, zr + S.ROOF_RC, ex1, zr + S.ROOF_RC + 0.16))
    draw_rc(v, rc, ins)
    v.rect(ex0, zr + S.ROOF_RC + 0.16, ex1, zr + S.ROOF_T, fc="#7a7d84", ec="k", lw="thin", z=2.7)
    # 너머 (용마루)
    v.rect(ex0, zr + S.ROOF_T, ex1, S.Z_TOP, fc="#ececec", ec="k", lw="thin", hatch="---", z=1.5)
    v.text((ex0 + ex1) / 2, (zr + S.ROOF_T + S.Z_TOP) / 2, "지붕면 (너머, 용마루까지)", 1.8, bg="#ececec")
    for u in (ex0, ex1):
        v.line([(u, zr + S.ROOF_T), (u, S.Z_TOP)], lw="thin")
    # 개구부 표시
    for o in S.openings(1) + S.openings(2):
        if not (o["a0"] <= y <= o["a1"]) or o["wall"] not in "EW":
            continue
        a = x0 if o["wall"] == "W" and o["floor"] == 1 else (S.B2[0] if o["wall"] == "W" else x1 - S.WALL)
        window_section(v, a, a + S.WALL, o["z0"], o["z1"], o["kind"])
    # 바닥·천장
    floor_layers(v, x0 + S.WALL, x1 - S.WALL, S.FL1, S.FLOOR1_LAYERS)
    floor_layers(v, S.B2[0] + S.WALL, x1 - S.WALL, S.FL2, S.FLOOR2_LAYERS)
    v.rect(x0 + O_RC0 + 0.15, z_s2t, S.TERRACE[2], z_s2t + 0.10, fc=INS_FC, ec="k", lw="fine", hatch="....", z=2)
    v.rect(x0 + O_RC0 + 0.15, z_s2t + 0.10, S.TERRACE[2], S.FL2 - 0.11, fc="#f2f2f2", ec="k", lw="fine", z=2)
    v.rect(x0 + O_RC0 + 0.15, S.FL2 - 0.11, S.TERRACE[2], S.FL2 - 0.05, fc="#c9a77c", ec="k", lw="fine", z=2)
    for zc, a, b in ((S.FL1 + S.CEIL_H, x0 + S.WALL, x1 - S.WALL), (S.FL2 + S.CEIL_H, S.B2[0] + S.WALL, x1 - S.WALL)):
        v.rect(a, zc, b, zc + 0.02, fc="#bbbbbb", ec="k", lw="fine", z=3)
    # 내벽 (잘린 것)
    for floor, zb, zt in ((1, S.FL1, z_s1b), (2, S.FL2, S.FL2 + S.CEIL_H)):
        for p in S.parts(floor):
            px0, py0, px1, py1 = p["rect"]
            if (py1 - py0) > (px1 - px0) and py0 <= y <= py1 and not any(d[0] <= y <= d[1] for d in p["doors"]):
                v.rect(px0, zb, px1, zt, fc=PART_FC, ec="k", lw="heavy", hatch="xx", z=3)
    # 너머의 문 (북쪽으로 보이는 것)
    for floor, fl, wy in ((1, S.FL1, 11.5), (2, S.FL2, 12.4), (2, S.FL2, 13.6)):
        for p in S.parts(floor):
            px0, py0, px1, py1 = p["rect"]
            if abs(py0 - wy) < 0.01:
                for a0, a1, *_ in p["doors"]:
                    v.rect(a0, fl, a1, fl + S.DOOR_H, ec="k", lw="thin", z=1.8)
    v.rect(3.0, S.FL1 + 1.0, 5.4, S.FL1 + 2.1, ec="k", lw="thin", z=1.8)       # 북측 주방창 (너머)
    # 실명
    for u, z, s_ in ((4.6, 1.5, "거실"), (8.8, 1.7, "화장실"), (11.1, 1.7, "현관"), (5.7, 4.6, "안방"),
                     (10.0, 4.6, "방2"), (2.55, 3.8, "테라스"), (8.0, 6.6, "천장 내부 (환기)")):
        v.text(u, z, s_, 2.6 if s_ != "천장 내부 (환기)" else 2.0, weight="bold", bg="white")
    return v


def section_B(sh, o=(80, 125)):
    v = sh.view(*o, 50, u0=7.6, v0=-2.7)
    xc = SEC_B_X
    _, y0, _, y1 = S.B1
    earth(v, 7.7, 18.3)
    rc, ins = [foundation_section(v, y0, y1)], []
    z_s1b = S.FL2 - S.SLAB
    z_s1t = z_s1b + S.SLAB_RC
    holes_s = [(o["z0"], o["z1"]) for o in S.openings(1) + S.openings(2) if o["wall"] == "S" and o["a0"] <= xc <= o["a1"]]
    r_, i_ = wall_section(y0, y0 + S.WALL, S.MAT_TOP, S.TOP2, "lo", holes_s)
    rc += r_
    ins += i_
    holes_n = [(o["z0"], o["z1"]) for o in S.openings(1) + S.openings(2) if o["wall"] == "N" and o["a0"] <= xc <= o["a1"]]
    r_, i_ = wall_section(y1 - S.WALL, y1, S.MAT_TOP, S.TOP2, "hi", holes_n)
    rc += r_
    ins += i_
    # S1 (계단 개구부에서 끊김)
    cut_from = min(o[1] for o in S.SLAB_OPENINGS if o[0] <= xc <= o[2])
    rc.append(sbox(y0, z_s1b, cut_from, z_s1t))
    g1 = [b for b in S.BEAMS if b["axis"] == "x"][0]
    rc.append(sbox(g1["at"] - g1["b"] / 2, z_s1t - g1["h"], g1["at"] + g1["b"] / 2, z_s1t))
    # 지붕
    r_roof, i_roof, top = roof_section_cross(v, lambda yy: yy)
    rc.append(r_roof)
    ins.append(i_roof)
    rb = S.RIDGE_BEAM
    rc.append(sbox(S.RIDGE_Y - rb["b"] / 2, S.Z_RIDGE_UNDER - rb["h"], S.RIDGE_Y + rb["b"] / 2, S.Z_RIDGE_UNDER + 0.05))
    # 계단 (1차, 절단)
    R, T = S.RISE, S.TREAD
    ys = S.STAIR[1]
    land_z = S.FL1 + S.N1 * R
    prof = [(ys, S.FL1)]
    for i in range(S.N1 - 1):
        prof += [(ys + i * T, S.FL1 + (i + 1) * R), (ys + (i + 1) * T, S.FL1 + (i + 1) * R)]
    prof += [(S.LANDING_Y, land_z), (y1 - S.WALL, land_z), (y1 - S.WALL, land_z - 0.15)]
    th = math.atan(R / T)
    d = R + 0.15 / math.cos(th)
    u_land = ys + (land_z - 0.15 - S.FL1 - R + d) * T / R
    u_start = ys + (d - R) * T / R
    prof += [(u_land, land_z - 0.15), (u_start, S.FL1)]
    rc.append(Polygon(prof))
    draw_rc(v, rc, ins)
    v.geom(top, fc="#7a7d84", ec="k", lw="thin", z=2.7)
    # 2차 계단 (너머)
    pts = [(S.LANDING_Y, land_z)]
    for i in range(S.RISERS - S.N1):
        u = S.LANDING_Y - i * T
        z = land_z + (i + 1) * R
        pts += [(u, z), (u - T, z)] if i < S.RISERS - S.N1 - 1 else [(u, z)]
    v.line(pts, lw="thin")
    v.line([(S.TOP_Y, S.FL2), (S.TOP_Y, z_s1b)], lw="thin")
    for i in range(S.N1):
        v.line([(ys + i * T, S.FL1 + (i + 1) * R + 0.9), (ys + (i + 1) * T, S.FL1 + (i + 1) * R + 0.9)], lw="fine")
    v.line([(ys, S.FL1 + R + 0.9), (S.LANDING_Y, land_z + 0.9)], lw="thin", color="#555555")
    v.text(16.2, 0.95, f"계단 {S.RISERS}단\n단높이 {S.RISE * 1000:.1f}\n단너비 {mm(S.TREAD)}",
           1.6, bg="white")
    for rail_x in (S.RAILS_2F[0][0][1],):
        v.rect(rail_x - 0.02, S.FL2, rail_x + 0.02, S.FL2 + S.RAIL_H, fc="#888888", ec="k", lw="fine", z=4)
    # 개구부
    for o in S.openings(1) + S.openings(2):
        if o["wall"] == "S" and o["a0"] <= xc <= o["a1"]:
            window_section(v, y0, y0 + S.WALL, o["z0"], o["z1"], o["kind"])
    # 바닥·천장
    floor_layers(v, y0 + S.WALL, y1 - S.WALL, S.FL1, S.FLOOR1_LAYERS)
    floor_layers(v, y0 + S.WALL, cut_from, S.FL2, S.FLOOR2_LAYERS)
    v.rect(y0 + S.WALL, S.FL1 + S.CEIL_H, ys, S.FL1 + S.CEIL_H + 0.02, fc="#bbbbbb", ec="k", lw="fine", z=3)
    v.rect(y0 + S.WALL, S.FL2 + S.CEIL_H, y1 - S.WALL, S.FL2 + S.CEIL_H + 0.02, fc="#bbbbbb", ec="k", lw="fine", z=3)
    for floor, zb, zt in ((1, S.FL1, z_s1b), (2, S.FL2, S.FL2 + S.CEIL_H)):
        for p in S.parts(floor):
            px0, py0, px1, py1 = p["rect"]
            if (px1 - px0) > (py1 - py0) and px0 <= xc <= px1 and not any(d[0] <= xc <= d[1] for d in p["doors"]):
                v.rect(py0, zb, py1, zt, fc=PART_FC, ec="k", lw="heavy", hatch="xx", z=3)
    for u, z, s_ in ((10.4, 1.6, "현관"), (12.6, 1.6, "홀"), (15.6, 3.2, "계단실"), (10.9, 4.6, "방2"),
                     (14.6, 4.6, "홀"), (13.0, 6.75, "천장 내부 (환기)")):
        v.text(u, z, s_, 2.6 if "천장" not in s_ else 2.0, weight="bold", bg="white")
    return v


def section_draw(sh, which, o=(80, 125)):
    v = section_A(sh, o) if which == "A" else section_B(sh, o)
    if which == "A":
        lo, hi, grid = 1.5, 12.5, S.GRID_X
    else:
        lo, hi, grid = 9.0, 17.0, S.GRID_Y
    for name, g in grid:
        v.line([(g, -1.35), (g, -2.2)], lw="fine", ls=(0, (12, 3, 2, 3)), color="#555555")
        v.bubble(g, -2.45, name, r=3.2)
    v.hdim([g for _, g in grid], -1.55)
    v.hdim([lo, hi], -2.0 + 0.0)
    zs = [S.FOOT_BOT, 0, S.FL1, S.FL1 + S.CEIL_H, S.FL2, S.FL2 + S.CEIL_H, S.TOP2, S.Z_TOP]
    v.vdim(zs, lo - 1.2, ext=lo - 0.6)
    v.vdim([0, S.Z_TOP], lo - 1.9)
    ru = (S.B2[2] + S.EAVE + 0.4) if which == "A" else (hi + S.EAVE + 0.4)
    for z, lab in ((S.Z_TOP, f"최고높이 +{mm(S.Z_TOP)}"), (S.TOP2, f"처마 +{mm(S.TOP2)}"),
                   (S.FL2 + S.CEIL_H, f"2층 반자 +{mm(S.FL2 + S.CEIL_H)}"), (S.FL2, f"2FL +{mm(S.FL2)}"),
                   (S.FL1 + S.CEIL_H, f"1층 반자 +{mm(S.FL1 + S.CEIL_H)}"), (S.FL1, f"1FL +{mm(S.FL1)}"),
                   (0, "GL ±0"), (S.FOOT_BOT, f"기초 하단 {mm(S.FOOT_BOT)}")):
        v.level(ru, z, lab, length=30)
    return v


def section_sheet(book, which):
    no = "A-401" if which == "A" else "A-402"
    sh = Sheet(book, no, f"단면도 {which}-{which}'", "1/50")
    section_draw(sh, which)
    sh.heading(20, 398, f"단면도 {which}-{which}'", "1/50", num="1")
    key = "y = 11,000 위치에서 북측을 봄" if which == "A" else "x = 11,650 위치에서 서측을 봄 (계단 절단)"
    sh.text(30, 384, f"절단 위치: 평면도 {which}-{which}' ({key})", 2.2)
    notes = ["지붕: 싱글 / 방수시트 / OSB 11 / 통기층 30 / PF보드 160 / RC 150",
             "외벽: 스터코 10 / PF보드 100 / RC 180 / 석고보드 9.5",
             "1층 바닥: 강마루 10 / 미장 50 / 기포 40 / XPS 특호 120",
             "    / PE필름 / 매트기초 400",
             "2층 바닥: 강마루 10 / 미장 40 / 기포 40 / RC 180",
             "테라스: 데크 / 보호몰탈 / 우레탄 도막방수 / PF보드 100 / RC 180",
             "기초: 매트 F1 THK400 + 외곽 기초보 FG1 (하단 GL-920)",
             "천장: 경량철골 천장틀 + 석고보드 9.5 2겹, 천장 내부 환기",
             "상세: A-501 구조단면 상세, 부재: S-001 부재일람표"]
    plan_notes(sh, [f"{i + 1}. {n_}" if not n_.startswith("    ") else n_ for i, n_ in
                    enumerate(notes)], y=300)
    sh.save()


# ---------------------------------------------------------------- 구조
def struct_plan(v, kind):
    x0, y0, x1, y1 = S.B1
    if kind == "F":
        v.rect(x0, y0, x1, y1, fc="#f2f2f2", ec="k", lw="cut", z=1)
        v.rect(x0 + S.FOOT_W, y0 + S.FOOT_W, x1 - S.FOOT_W, y1 - S.FOOT_W, ec="k", lw="thin", ls="--", z=2)
        walls = [sbox(x0 + O_RC0, y0 + O_RC0, x1 - O_RC0, y1 - O_RC0).difference(
            sbox(x0 + S.WALL, y0 + S.WALL, x1 - S.WALL, y1 - S.WALL))]
        v.geom(unary_union(walls), fc=RC_FC, ec="k", lw="thin", hatch="////", z=3)
        v.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.6, "F1  매트기초 THK400", 2.2, weight="bold", bg="#f2f2f2")
        v.text((x0 + x1) / 2, (y0 + y1) / 2 - 0.2, "상·하단 D13@200 양방향", 1.8, bg="#f2f2f2")
        v.text((x0 + x1) / 2, y0 + 0.3 + 0.15, "FG1 (600 x 1,000, 하단 GL-920)", 1.6, bg="#f2f2f2")
        v.text((x0 + x1) / 2, (y0 + y1) / 2 - 1.2, f"허용지내력 fe ≥ 150 kN/㎡ (평판재하시험 확인)", 1.6, bg="#f2f2f2")
        return
    if kind == "2":
        rc = unary_union([sbox(S.TERRACE[2], y0, x1, y1), sbox(x0, y0, S.TERRACE[2], y1)])
        for o in S.SLAB_OPENINGS:
            rc = rc.difference(sbox(o[0], o[1], o[2], o[3]))
        v.geom(rc, fc="#f6f6f6", ec="k", lw="cut", z=1)
        for o in S.SLAB_OPENINGS:
            v.line([(o[0], o[1]), (o[2], o[3])], lw="fine")
            v.line([(o[0], o[3]), (o[2], o[1])], lw="fine")
        v.text(11.15, 15.2, "계단\n개구부", 1.6, bg="white")
        walls = sbox(x0 + O_RC0, y0 + O_RC0, x1 - O_RC0, y1 - O_RC0).difference(
            sbox(x0 + S.WALL, y0 + S.WALL, x1 - S.WALL, y1 - S.WALL))
        v.geom(walls, fc=RC_FC, ec="k", lw="thin", hatch="////", z=3)
        for b in S.BEAMS:
            hb = b["b"] / 2
            if b["axis"] == "x":
                v.line([(b["r0"], b["at"] - hb), (b["r1"], b["at"] - hb)], lw="vis", ls="--")
                v.line([(b["r0"], b["at"] + hb), (b["r1"], b["at"] + hb)], lw="vis", ls="--")
                v.text(4.6, b["at"] + 0.35, b["id"], 2.0, weight="bold", bg="white")
            else:
                v.line([(b["at"] - hb, b["r0"]), (b["at"] - hb, b["r1"])], lw="vis", ls="--")
                v.line([(b["at"] + hb, b["r0"]), (b["at"] + hb, b["r1"])], lw="vis", ls="--")
                v.text(b["at"] + 0.45, 10.4, b["id"], 2.0, weight="bold", bg="white", rot=90)
        v.text(5.6, 11.2, "S1 THK180", 1.9, bg="white")
        v.text(10.2, 11.2, "S1 THK180", 1.9, bg="white")
        v.text(5.6, 15.0, "S1 THK180", 1.9, bg="white")
        v.text(2.55, 13.0, "S2\nTHK180\n(단차)", 1.7, bg="white")
        return
    # 지붕
    ex0, ex1, ey0, ey1 = S.B2[0] - S.EAVE, S.B2[2] + S.EAVE, S.B2[1] - S.EAVE, S.B2[3] + S.EAVE
    v.rect(ex0, ey0, ex1, ey1, fc="#f6f6f6", ec="k", lw="cut", z=1)
    b2 = S.B2
    walls = sbox(b2[0] + O_RC0, b2[1] + O_RC0, b2[2] - O_RC0, b2[3] - O_RC0).difference(
        sbox(b2[0] + S.WALL, b2[1] + S.WALL, b2[2] - S.WALL, b2[3] - S.WALL))
    v.geom(walls, fc=RC_FC, ec="k", lw="thin", hatch="////", z=3)
    hb = S.RIDGE_BEAM["b"] / 2
    v.line([(b2[0] + S.WALL, S.RIDGE_Y - hb), (b2[2] - S.WALL, S.RIDGE_Y - hb)], lw="vis", ls="--")
    v.line([(b2[0] + S.WALL, S.RIDGE_Y + hb), (b2[2] - S.WALL, S.RIDGE_Y + hb)], lw="vis", ls="--")
    v.text(8.0, S.RIDGE_Y + 0.4, "RB1 (용마루보 300x400)", 1.9, weight="bold", bg="white")
    v.text(8.0, 11.0, "RS1 THK150 (경사 5/10)", 1.9, bg="white")
    v.text(8.0, 15.0, "RS1 THK150 (경사 5/10)", 1.9, bg="white")
    v.text(8.0, ey0 + 0.22, "처마 캔틸레버 500", 1.5, bg="white")


def struct_sheets(book):
    sh = Sheet(book, "S-001", "구조 일반사항·부재일람표", "NONE")
    sh.heading(20, 398, "구조 일반사항")
    gen = [
        "1. 설계기준: 건축구조기준 (KDS 41), 콘크리트구조 설계기준 (KDS 14 20)",
        f"2. 재료: 콘크리트 fck = {S.FCK} MPa (기초·구조체), 철근 SD{S.FY} (D10~D22), 이음·정착은 KDS 14 20 52",
        "3. 하중: 고정하중은 실제 구성으로 산정, 활하중 주거 2.0 kN/㎡, 지붕 1.0 kN/㎡ (KDS 41 10 15)",
        "4. 적설·풍하중: 경산시 지역 기준값 적용 (KDS 41 12 00) — 구조계산서에서 확정",
        "5. 내진: 2층 이상 건축물 → 구조안전 확인 대상 (건축법 시행령 제32조), 내진등급 II",
        "6. 지반: 허용지내력 fe ≥ 150 kN/㎡ 가정 — 지반조사(평판재하시험) 후 기초 확정",
        "7. 피복두께: 흙에 접하는 기초 75, 흙에 접하는 벽 50, 실내 슬래브·벽 20, 보 40",
        "8. 개구부 보강: 벽·슬래브 개구부 둘레 2-D13, 모서리 사선보강 2-D13 (L=1,000)",
        "9. 타설 순서: 매트기초 → 1층 벽 → 2층 슬래브·보 → 2층 벽 → 지붕, 이음은 전단력이 작은 곳",
        "10. 본 도면의 부재 크기·배근은 예비 산정값이며, 구조계산서와 구조기술사 검토로 확정한다.",
    ]
    for i, s_ in enumerate(gen):
        sh.text(24, 380 - i * 7, s_, 2.2)
    sh.heading(20, 290, "부재일람표")
    rows = [("부호", "부재", "크기", "배근", "비고")] + [tuple(m) for m in S.MEMBERS]
    sh.table(24, 278, [18, 38, 52, 92, 52], rows, rh=8.0, size=2.2)
    sh.heading(320, 290, "하중표 (kN/㎡, 추정)")
    lrows = [("부위", "고정하중", "활하중"), ("지붕 (경사)", "5.4", "1.0"), ("2층 바닥", "6.2", "2.0"),
             ("테라스", "7.0", "3.0"), ("계단", "6.5", "3.0")]
    sh.table(324, 278, [50, 34, 34], lrows, rh=8.0, size=2.2, aligns=["left", "center", "center"])
    sh.text(324, 230, "※ 고정하중은 마감 구성으로 추정한 값이며 구조계산서에서 확정합니다.", 1.9)
    sh.save()

    sh = Sheet(book, "S-101", "구조 평면도", "1/100")
    for i, (kind, title) in enumerate((("F", "기초 구조평면도"), ("2", "2층 바닥 구조평면도"), ("R", "지붕 구조평면도"))):
        ox = 52 + i * 182
        v = sh.view(ox, 230, 100, u0=1.5, v0=9.0)
        struct_plan(v, kind)
        for name, g in S.GRID_X:
            v.line([(g, 7.4), (g, 18.0)], lw="fine", ls=(0, (12, 3, 2, 3)), color="#555555", z=1)
            v.bubble(g, 7.0, name, r=2.6)
        for name, g in S.GRID_Y:
            v.line([(0.4, g), (13.2, g)], lw="fine", ls=(0, (12, 3, 2, 3)), color="#555555", z=1)
            v.bubble(0.05, g, name, r=2.6)
        v.hdim([g for _, g in S.GRID_X], 6.2, size=1.6)
        v.hdim([1.5, 12.5], 5.6, size=1.7)
        sh.heading(ox - 12, 360, title, "1/100", num=str(i + 1))
    sh.text(24, 160, "범례", 2.8, weight="bold")
    sh.ax.add_patch(MPoly([(24, 148), (36, 148), (36, 153), (24, 153)], closed=True, fc=RC_FC, ec="k", hatch="////",
                          lw=LW["thin"] * PT, zorder=7))
    sh.text(40, 150.5, "W1 RC 내력벽 THK180 (해당 층 아래 벽)", 2.1)
    sh.ax.plot([24, 36], [141, 141], color="k", ls="--", lw=LW["vis"] * PT)
    sh.ax.plot([24, 36], [138.5, 138.5], color="k", ls="--", lw=LW["vis"] * PT)
    sh.text(40, 139.8, "보 (슬래브 아래)", 2.1)
    for i, s_ in enumerate(["※ TG1: 2층 서측 외벽(X2열)이 1층 거실 위에 놓이므로 전이보로 받친다.",
                            "※ G1·B1: 2층 바닥 슬래브 경간을 5.7 m 이하로 나눈다.",
                            "※ RB1: 동·서 박공벽에 걸친 용마루보, 지붕 슬래브 RS1을 지지한다.",
                            "※ 계단: RC 계단 (경사판 THK150), 1층 바닥·참·2층 슬래브에 정착."]):
        sh.text(24, 126 - i * 7, s_, 2.1)
    sh.save()


# ---------------------------------------------------------------- 상세
def numbered(v, items, tx, ty0, step=5.2):
    for i, ((u, z), s_) in enumerate(items):
        v.leader(u, z, tx, ty0 - i * step, f"{i + 1}. {s_}", size=1.9)



def detail_1(sh, o):
    # D1 기초·외벽·1층 바닥 (u = 외벽 바깥면에서 안쪽으로)
    v = sh.view(*o, 20, u0=-0.5, v0=-1.25)
    v.rect(-0.5, -1.25, 1.3, 0, fc="#f3eee6", ec="none", hatch="\\\\\\", z=0.5)
    rc = [sbox(0, S.FOOT_BOT, S.FOOT_W, S.MAT_BOT), sbox(0, S.MAT_BOT, 1.3, S.MAT_TOP),
          sbox(O_RC0, S.MAT_TOP, S.WALL, 0.75)]
    ins = [sbox(S.W_FIN, 0.0, O_INS1, 0.75), sbox(-0.05, S.FOOT_BOT + 0.05, 0.0, 0.0)]
    v.rect(-0.0, 0.0, S.W_FIN, 0.75, fc="#ffffff", ec="k", lw="fine", z=2)
    v.rect(0.0, S.FOOT_BOT - 0.06, S.FOOT_W, S.FOOT_BOT, fc="#cfcfcf", ec="k", lw="fine", z=1.5)
    v.rect(0.0, S.FOOT_BOT - 0.26, S.FOOT_W, S.FOOT_BOT - 0.06, fc="white", ec="k", lw="fine", hatch="oo", z=1.5)
    v.rect(S.FOOT_W, S.MAT_BOT - 0.06, 1.3, S.MAT_BOT, fc="#cfcfcf", ec="k", lw="fine", z=1.5)
    v.rect(S.FOOT_W, S.MAT_BOT - 0.26, 1.3, S.MAT_BOT - 0.06, fc="white", ec="k", lw="fine", hatch="oo", z=1.5)
    draw_rc(v, rc, ins)
    v.rect(-0.07, S.FOOT_BOT + 0.05, -0.05, 0.0, fc="#555555", ec="k", lw="fine", z=2)
    floor_layers(v, S.WALL, 1.3, S.FL1, S.FLOOR1_LAYERS)
    v.rect(S.WALL - S.W_GYP, S.FL1, S.WALL, 0.75, fc="white", ec="k", lw="fine", z=2.8)
    v.rect(S.WALL, S.FL1, S.WALL + 0.012, S.FL1 + 0.08, fc="#999999", ec="k", lw="fine", z=3)
    v.rect(-0.03, 0.0, 0.0, 0.3, fc="#bbbbbb", ec="k", lw="fine", z=3)
    v.line([(-0.5, 0.0), (0.0, 0.0)], lw=0.7)
    v.line([(-0.5, 0.75), (1.3, 0.75)], lw="fine", ls=(0, (6, 2)))
    v.line([(1.3, -1.25), (1.3, 0.75)], lw="fine", ls=(0, (6, 2)))
    for z, lab in ((S.FL1, "1FL +300"), (0, "GL ±0"), (S.FOOT_BOT, "-920")):
        v.level(-0.5, z, lab, side="left", length=12)
    numbered(v, [((0.005, 0.5), "스터코 마감 THK10 (준불연)"), ((0.06, 0.6), "PF보드 THK100 (준불연, 외단열)"),
                 ((0.2, 0.62), "RC 외벽 W1 THK180"), ((0.296, 0.68), "석고보드 9.5 + 실크벽지"),
                 ((-0.015, 0.2), "걸레받이 화강석 THK30"),
                 ((0.8, S.FL1 - 0.005), "강마루 THK10"), ((0.9, 0.265), "방바닥 미장 THK50 (XL 온수배관)"),
                 ((1.0, 0.22), "경량기포콘크리트 THK40"), ((1.1, 0.14), "압출법단열판 특호 THK120"),
                 ((1.2, S.MAT_TOP), "PE필름 0.1mm 2겹 (방습)"), ((1.0, -0.1), "매트기초 F1 THK400 (D13@200)"),
                 ((0.3, -0.6), "기초보 FG1 (하단 GL-920)"), ((0.9, S.MAT_BOT - 0.03), "버림콘크리트 THK60"),
                 ((0.9, S.MAT_BOT - 0.16), "잡석다짐 THK200"), ((-0.025, -0.5), "기초 외단열 XPS THK50"),
                 ((-0.06, -0.8), "도막방수 + 배수판 + 보호판")],
             v.P(1.3, 0)[0] + 8, v.P(0, 0.75)[1] + 8)

    return v


def detail_2(sh, o):
    # D2 2층 바닥·외벽 (남측, 1층 거실창 W1 머리)
    v = sh.view(*o, 20, u0=-0.4, v0=2.35)
    zb = S.FL2 - S.SLAB
    w1 = [o for o in S.OPENINGS if o["id"] == "W1"][0]
    rc = [sbox(O_RC0, w1["z1"], S.WALL, 4.1), sbox(O_RC0, zb, 1.5, zb + S.SLAB_RC)]
    ins = [sbox(S.W_FIN, w1["z1"], O_INS1, 4.1)]
    v.rect(0.0, w1["z1"], S.W_FIN, 4.1, fc="white", ec="k", lw="fine", z=2)
    draw_rc(v, rc, ins)
    floor_layers(v, S.WALL, 1.5, S.FL2, S.FLOOR2_LAYERS)
    v.rect(S.WALL, S.FL1 + S.CEIL_H, 1.5, S.FL1 + S.CEIL_H + 0.019, fc="#bbbbbb", ec="k", lw="fine", z=3)
    for u in (0.45, 0.9, 1.35):
        v.line([(u, S.FL1 + S.CEIL_H + 0.02), (u, zb)], lw="fine")
    window_section(v, 0, S.WALL, 2.35, w1["z1"], "win")
    v.rect(S.W_FIN, w1["z1"] - 0.02, S.WALL, w1["z1"], fc="#999999", ec="k", lw="fine", z=3)
    v.line([(-0.4, 4.1), (1.5, 4.1)], lw="fine", ls=(0, (6, 2)))
    v.line([(-0.4, 2.35), (1.5, 2.35)], lw="fine", ls=(0, (6, 2)))
    for z, lab in ((S.FL2, "2FL +3,300"), (S.FL1 + S.CEIL_H, "1층 반자 +2,700")):
        v.level(-0.4, z, lab, side="left", length=12)
    numbered(v, [((0.8, S.FL2 - 0.005), "강마루 THK10"), ((0.9, S.FL2 - 0.03), "방바닥 미장 THK40"),
                 ((1.0, S.FL2 - 0.07), "경량기포콘크리트 THK40"), ((1.1, zb + 0.09), "2층 슬래브 S1 THK180"),
                 ((0.2, 3.7), "RC 외벽 W1 THK180"), ((0.06, 3.9), "PF보드 THK100 (창 둘레 단열 연속)"),
                 ((0.15, w1["z1"] + 0.1), "인방: 개구부 보강 2-D13"), ((0.15, 2.45), "W1 시스템창호 (삼중 로이)"),
                 ((0.9, S.FL1 + S.CEIL_H + 0.01), "석고보드 9.5 2겹 + 도장 (천장)"),
                 ((1.35, 2.85), "경량철골 천장틀 (M-BAR)")],
             v.P(1.5, 0)[0] + 8, v.P(0, 4.1)[1] + 4)

    return v


def detail_3(sh, o):
    # D3 처마
    v = sh.view(*o, 20, u0=-0.75, v0=5.55)
    z_u = lambda u: S.TOP2 + u * S.ROOF_PITCH  # noqa: E731
    u_a, u_b = -S.EAVE, 1.4

    def slope(t0, t1):
        return Polygon([(u_a, z_u(u_a) + t0), (u_b, z_u(u_b) + t0), (u_b, z_u(u_b) + t1), (u_a, z_u(u_a) + t1)])
    rc = [sbox(O_RC0, 5.55, S.WALL, S.TOP2 + S.WALL * S.ROOF_PITCH), slope(0, S.ROOF_RC)]
    ins = [sbox(S.W_FIN, 5.55, O_INS1, S.TOP2), slope(S.ROOF_RC, S.ROOF_RC + 0.16)]
    draw_rc(v, rc, ins)
    v.geom(slope(S.ROOF_RC + 0.16, S.ROOF_RC + 0.19), fc="#e8dcc8", ec="k", lw="fine", z=2.8)
    v.geom(slope(S.ROOF_RC + 0.19, S.ROOF_RC + 0.201), fc="#c9a77c", ec="k", lw="fine", z=2.8)
    v.geom(slope(S.ROOF_RC + 0.201, S.ROOF_T), fc="#555555", ec="k", lw="fine", z=2.8)
    v.rect(u_a - 0.02, z_u(u_a), u_a, z_u(u_a) + S.ROOF_T, fc="#bfc3c8", ec="k", lw="fine", z=3)
    v.ax.add_patch(Arc(v.P(u_a - 0.09, z_u(u_a) + 0.05), 0.16 * v.k, 0.16 * v.k, theta1=180, theta2=360,
                       lw=LW["thin"] * PT, zorder=4))
    v.line([(u_a, z_u(u_a)), (0.0, z_u(u_a))], lw="thin")
    v.rect(S.WALL, S.FL2 + S.CEIL_H, u_b, S.FL2 + S.CEIL_H + 0.019, fc="#bbbbbb", ec="k", lw="fine", z=3)
    v.rect(0.0, 5.55, S.W_FIN, S.TOP2, fc="white", ec="k", lw="fine", z=2)
    v.line([(u_b, 5.55), (u_b, z_u(u_b) + S.ROOF_T)], lw="fine", ls=(0, (6, 2)))
    v.line([(-0.75, 5.55), (u_b, 5.55)], lw="fine", ls=(0, (6, 2)))
    v.level(-0.75, S.TOP2, "처마 +6,300", side="left", length=10)
    numbered(v, [((1.2, z_u(1.2) + S.ROOF_T - 0.005), "아스팔트 싱글 + 자착식 방수시트"),
                 ((1.1, z_u(1.1) + S.ROOF_RC + 0.195), "OSB THK11"),
                 ((1.0, z_u(1.0) + S.ROOF_RC + 0.175), "각재 통기층 THK30 (처마→용마루 통기)"),
                 ((0.9, z_u(0.9) + S.ROOF_RC + 0.08), "PF보드 THK160 (준불연)"),
                 ((0.8, z_u(0.8) + 0.07), "지붕 슬래브 RS1 THK150"),
                 ((u_a - 0.09, z_u(u_a)), "알루미늄 처마홈통 W150"),
                 ((-0.25, z_u(-0.5)), "알루미늄 소핏 (펀칭 환기)"),
                 ((0.06, 5.9), "외벽 PF보드 → 지붕 단열과 연속 (열교 방지)"),
                 ((0.9, S.FL2 + S.CEIL_H + 0.01), "2층 천장: 석고보드 9.5 2겹")],
             v.P(u_b, 0)[0] + 8, v.P(0, 7.4)[1])

    return v


def detail_4(sh, o):
    # D4 테라스·파라펫·2층 문턱 (u = x)
    v = sh.view(*o, 20, u0=1.2, v0=2.4)
    zt = 4.75
    x0 = S.TERRACE[0]
    z_s2b = S.FL2 - S.SLAB - S.TERRACE_DROP
    z_s2t = z_s2b + S.SLAB_RC
    z_s1b = S.FL2 - S.SLAB
    z_s1t = z_s1b + S.SLAB_RC
    tg = [b for b in S.BEAMS if b["id"] == "TG1"][0]
    rc = [sbox(x0 + O_RC0, 2.4, x0 + O_RC0 + 0.15, S.FL2 + S.RAIL_H), sbox(x0 + O_RC0, z_s2b, 3.65, z_s2t),
          sbox(tg["at"] - tg["b"] / 2, z_s1t - tg["h"], tg["at"] + tg["b"] / 2, z_s1t), sbox(3.5, z_s1b, 4.3, z_s1t)]
    ins = [sbox(x0, 2.4, x0 + O_INS1, S.FL2 + S.RAIL_H), sbox(x0 + O_RC0 + 0.15, z_s2t, 3.5, z_s2t + 0.10)]
    draw_rc(v, rc, ins)
    v.rect(x0 + O_RC0 + 0.15, z_s2t + 0.10, 3.5, S.FL2 - 0.11, fc="#f2f2f2", ec="k", lw="fine", z=2)
    for seg in ([(x0 + O_RC0 + 0.15, S.FL2 - 0.11), (3.5, S.FL2 - 0.11)],
                [(x0 + O_RC0 + 0.15, S.FL2 - 0.11), (x0 + O_RC0 + 0.15, S.FL2 + 0.2)],
                [(3.5, S.FL2 - 0.11), (3.5, S.FL2 + 0.2)]):
        v.line(seg, lw="vis", color="#0050a0")
    for u in (1.9, 2.5, 3.1):
        v.rect(u - 0.04, S.FL2 - 0.11, u + 0.04, S.FL2 - 0.07, fc="#777777", ec="k", lw="fine", z=3)
    v.rect(x0 + O_RC0 + 0.15, S.FL2 - 0.07, 3.48, S.FL2 - 0.05, fc="#c9a77c", ec="k", lw="fine", z=3)
    v.rect(x0 - 0.04, S.FL2 + S.RAIL_H, x0 + O_RC0 + 0.19, S.FL2 + S.RAIL_H + 0.03, fc="#bfc3c8", ec="k", lw="fine", z=3)
    floor_layers(v, 3.8, 4.3, S.FL2, S.FLOOR2_LAYERS)
    window_section(v, 3.5, 3.8, S.FL2, zt, "door")
    v.rect(3.5, S.FL2, 3.8, S.FL2 + 0.05, fc="#666666", ec="k", lw="fine", z=4)
    v.rect(x0 + O_RC0 + 0.15, S.FL1 + S.CEIL_H, 4.3, S.FL1 + S.CEIL_H + 0.019, fc="#bbbbbb", ec="k", lw="fine", z=3)
    v.line([(4.3, 2.4), (4.3, zt)], lw="fine", ls=(0, (6, 2)))
    v.line([(1.2, 2.4), (4.3, 2.4)], lw="fine", ls=(0, (6, 2)))
    v.line([(3.3, zt), (4.3, zt)], lw="fine", ls=(0, (6, 2)))
    for z, lab in ((S.FL2 + S.RAIL_H, "+4,500"), (S.FL2, "2FL +3,300 (테라스 +3,250)")):
        v.level(1.2, z, lab, side="left", length=12)
    numbered(v, [((x0 + 0.1, S.FL2 + S.RAIL_H + 0.015), "알루미늄 두겁 (안쪽 구배)"),
                 ((x0 + 0.2, 3.9), "RC 파라펫 THK150 + 외단열 PF 100, H1,200"),
                 ((3.65, 4.3), "D2 테라스문 (문턱 방수턱 50)"),
                 ((2.2, S.FL2 - 0.06), "합성목재 데크 + 받침 (높이 조절)"),
                 ((2.0, S.FL2 - 0.11), "우레탄 도막방수 (치켜올림 300)"),
                 ((2.4, S.FL2 - 0.15), "보호몰탈 (구배 1/100)"),
                 ((2.8, z_s2t + 0.05), "PF보드 THK100"),
                 ((2.6, z_s2b + 0.09), "테라스 슬래브 S2 THK180"),
                 ((3.65, z_s1t - 0.4), "전이보 TG1 300x700")],
             v.P(4.3, 0)[0] + 8, v.P(0, zt)[1])
    return v


def detail_sheet(book):
    sh = Sheet(book, "A-501", "구조단면 상세", "1/20")
    detail_1(sh, (70, 255))
    sh.heading(20, 398, "상세 1  기초·외벽·1층 바닥", "1/20", num="1")
    detail_2(sh, (345, 262))
    sh.heading(300, 398, "상세 2  2층 바닥·외벽", "1/20", num="2")
    detail_3(sh, (70, 70))
    sh.heading(20, 200, "상세 3  처마", "1/20", num="3")
    detail_4(sh, (330, 70))
    sh.heading(300, 200, "상세 4  테라스·파라펫", "1/20", num="4")
    sh.save()


# ---------------------------------------------------------------- 표지·일람표
def u_value(layers_lambda, rsi=0.11, rso=0.043):
    return 1 / (rsi + rso + sum(t / lam for t, lam in layers_lambda))


U_WALL = u_value([(0.01, 0.9), (0.10, 0.020), (0.18, 1.6), (0.0095, 0.18)])
U_ROOF = u_value([(0.15, 1.6), (0.16, 0.020), (0.011, 0.13)], rsi=0.086, rso=0.086)
U_FLOOR = u_value([(0.01, 0.15), (0.05, 1.4), (0.04, 0.16), (0.12, 0.027), (0.40, 1.6)], rsi=0.086, rso=0.0)

SHEETS = [
    ("A-000", "표지·건축개요·법규검토", "-"), ("A-001", "면적표·창호일람표·실내재료마감표", "-"),
    ("A-101", "배치도", "1/100"), ("A-201", "1층 평면도", "1/50"), ("A-202", "2층 평면도", "1/50"),
    ("A-203", "지붕 평면도", "1/50"), ("A-301", "남측 입면도", "1/50"), ("A-302", "북측 입면도", "1/50"),
    ("A-303", "동측 입면도", "1/50"), ("A-304", "서측 입면도", "1/50"), ("A-401", "단면도 A-A'", "1/50"),
    ("A-402", "단면도 B-B'", "1/50"), ("A-501", "구조단면 상세", "1/20"),
    ("S-001", "구조 일반사항·부재일람표", "-"), ("S-101", "구조 평면도", "1/100"),
]


def cover_sheet(book):
    sh = Sheet(book, "A-000", "표지·건축개요·법규검토", "NONE")
    sh.text(22, 395, S.PROJECT, 8.0, weight="bold")
    sh.text(22, 382, "인허가·실시설계 도서 (초안)", 3.6, color="#444444")
    img = HERE / "images" / "exterior.png"
    if img.exists():
        sh.ax.imshow(plt.imread(str(img)), extent=(22, 202, 225, 360), zorder=3)
    sh.heading(20, 212, "건축개요")
    rows = [("구분", "내용"), ("대지위치", "경상북도 경산시 진량읍 신제리·다문리 일원"),
            ("", "경산4일반산업단지 단독주택용지 (필지번호 미정)"), ("지역·지구", S.ZONE),
            ("용도", S.USE), ("구조", S.STRUCTURE + ", 박공지붕"),
            ("대지면적", f"{S.LOT_AREA:.2f}㎡"), ("건축면적", f"{S.BUILDING_AREA:.2f}㎡"),
            ("연면적", f"{S.GFA:.2f}㎡ (1층 {S.AREA_1F:.2f} / 2층 {S.AREA_2F:.2f})"),
            ("건폐율 / 용적률", f"{S.BUILDING_AREA / S.LOT_AREA:.2%} / {S.GFA / S.LOT_AREA:.2%}"),
            ("규모 / 높이", f"지상 2층 / {S.Z_TOP:.2f} m (층고 3.0 m)"),
            ("주차 / 조경", f"{len(S.PARKING)}대 / {S.LANDSCAPE:.2f}㎡"),
            ("단열 (계획 U, W/㎡K)", f"외벽 {U_WALL:.3f} / 지붕 {U_ROOF:.3f} / 바닥 {U_FLOOR:.3f} / 창 1.0 이하")]
    sh.table(22, 202, [40, 140], rows, rh=8.6, size=2.2)
    sh.heading(222, 398, "도면 목록")
    sh.table(224, 388, [24, 84, 22], [("번호", "도면명", "축척")] + SHEETS, rh=7.4, size=2.1,
             aligns=["center", "left", "center"])
    sh.heading(372, 398, "법규 검토")
    rows = [("항목", "계획", "기준", "판정")] + [(n, val, lim, "적합" if ok else "부적합") for n, val, lim, ok, _ in ROWS]
    y = sh.table(374, 388, [22, 92, 82, 14], rows, rh=8.0, size=1.9)
    sh.text(374, y - 7, SUMMARY, 1.8, color="#444444")
    sh.text(374, y - 14, "※ 기준값은 공개 자료 기준이며 해당 필지의 지구단위계획 결정도서로 확인이 필요합니다.", 1.8,
            color="#444444")
    sh.save()


def schedule_sheet(book):
    sh = Sheet(book, "A-001", "면적표·창호일람표·실내재료마감표", "NONE")
    sh.heading(20, 398, "면적표")
    rows = [("층", "바닥면적(㎡)", "용도")] + [("1층", f"{S.AREA_1F:.2f}", "단독주택"), ("2층", f"{S.AREA_2F:.2f}", "단독주택"),
                                            ("합계", f"{S.GFA:.2f}", "")]
    y = sh.table(22, 388, [22, 34, 34], rows, rh=7.0, size=2.1, aligns=["center", "right", "center"])
    rows = [("층", "실명", "면적(㎡)")] + [(f"{r['floor']}층", r["name"], f"{S.room_area(r):.2f}") for r in S.ROOMS]
    sh.table(22, y - 8, [16, 40, 34], rows, rh=6.6, size=2.1, aligns=["center", "left", "right"])
    sh.text(22, 140, "※ 바닥면적: 외벽 중심선 (외단열 포함 벽두께의 중심)", 1.8)
    sh.text(22, 134, "※ 실면적: 마감면 기준 안목치수", 1.8)
    sh.heading(130, 398, "창호일람표")
    rows = [("기호", "층", "위치", "규격 W x H", "하단", "형식·사양")]
    for o in S.OPENINGS:
        rows.append((o["id"], f"{o['floor']}F", o["room"], f"{mm(o['a1'] - o['a0'])} x {mm(o['z1'] - o['z0'])}",
                     f"FL+{mm(o['z0'] - (S.FL1 if o['floor'] == 1 else S.FL2))}", o["spec"]))
    counts = {}
    for p in S.PARTS:
        for d in p["doors"]:
            if d[4] == "door":
                counts[d[5]] = counts.get(d[5], 0) + 1
    for k, (desc, w, h) in S.INNER_DOORS.items():
        rows.append((k, "1·2F", f"{counts.get(k, 0)}개소", f"{mm(w)} x {mm(h)}", "FL", desc))
    y = sh.table(132, 388, [16, 14, 26, 36, 22, 140], rows, rh=7.0, size=2.0,
                 aligns=["center", "center", "left", "center", "center", "left"])
    sh.heading(130, y - 14, "실내재료마감표")
    rows = [("층", "실명", "바닥", "걸레받이", "벽", "천장", "반자높이")]
    for r in S.ROOMS:
        f = r["fin"]
        rows.append((f"{r['floor']}F", r["name"], f[0], f[1], f[2], f[3], "-" if r["name"] == "테라스" else mm(S.CEIL_H)))
    sh.table(132, y - 24, [12, 22, 66, 34, 40, 64, 18], rows, rh=6.6, size=1.9,
             aligns=["center", "left", "left", "left", "left", "left", "center"])
    sh.save()


# ---------------------------------------------------------------- main
def main():
    OUT.mkdir(exist_ok=True)
    path = OUT / "house_drawings.pdf"
    with PdfPages(path) as book:
        cover_sheet(book)
        schedule_sheet(book)
        site_sheet(book)
        plan_sheet(book, 1)
        plan_sheet(book, 2)
        roof_sheet(book)
        for no, w in (("A-301", "S"), ("A-302", "N"), ("A-303", "E"), ("A-304", "W")):
            elevation_sheet(book, no, w)
        section_sheet(book, "A")
        section_sheet(book, "B")
        detail_sheet(book)
        struct_sheets(book)
        book.infodict()["Title"] = S.PROJECT + " 도면"
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
