# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "shapely>=2.0", "koreanize-matplotlib>=0.1.1", "setuptools", "pypdf>=4"]
# ///
"""경일대학교 건축학부 A3 양식(templates/kiu_a3_frame.pdf)에 도면 세트를 앉힌다.

실행: uv run drawings_a3.py  ->  drawings/house_drawings_A3.pdf
도면 내용은 drawings.py의 그리기 함수를 그대로 쓰고, 이 파일은 A3 배치와 표제란만 정한다.
양식 PDF를 배경으로 깔고 그 위에 도면을 겹친다 (축척은 표기 그대로 A3 출력 기준).
"""

import io
from pathlib import Path

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon as MPoly
from pypdf import PdfReader, PdfWriter

import drawings as D
import spec as S
from check import ROWS, SUMMARY

HERE = Path(__file__).parent
TEMPLATE = HERE / "templates" / "kiu_a3_frame.pdf"
OUT = HERE / "drawings" / "house_drawings_A3.pdf"

DRAWN_BY = "연제욱 (20202672)"
COURSE = "건축설계"
TITLE_LINES = ("경산 진량", "단독주택", "신축공사")
NOTE_BOX = (377.3, 246.0, 418.6, 112.0)          # x0, y_top, x1, y_bottom (양식 NOTE 칸)


def text_width(s, size):
    return sum(size * (1.40 if ord(c) > 0x2E80 else 0.78) for c in s)


def wrap(s, max_mm, size):
    out, line = [], ""
    for word in s.split(" "):
        cand = (line + " " + word) if line else word
        if text_width(cand, size) <= max_mm:
            line = cand
            continue
        if line:
            out.append(line)
        while text_width(word, size) > max_mm:          # 긴 낱말은 글자 단위로 자름
            cut = len(word)
            while text_width(word[:cut], size) > max_mm:
                cut -= 1
            out.append(word[:cut])
            word = word[cut:]
        line = word
    if line:
        out.append(line)
    return out


class FrameSheet(D.Sheet):
    """A3 양식 위에 겹쳐 그릴 투명한 시트. 표제란 칸만 채운다."""
    W, H = 420.0, 297.0

    def frame(self):
        ax = self.ax
        # 양식에 들어 있는 다른 과제명을 가리고 이 공사명으로 바꾼다
        ax.add_patch(MPoly([(376.4, 257.0), (419.2, 257.0), (419.2, 292.6), (376.4, 292.6)], closed=True,
                           fc="white", ec="none", zorder=7.5))
        for i, line in enumerate(TITLE_LINES):
            self.text(397.8, 284.0 - i * 7.3, line, 4.4, ha="center")
        self.text(404.0, 251.0, COURSE, 1.9, ha="center")
        self.text(404.0, 35.3, DRAWN_BY, 1.9, ha="center")
        self.text(404.0, 28.9, D.DATE, 2.0, ha="center")
        self.text(398.0, 18.4, self.title, 2.6 if len(self.title) < 12 else 2.0, ha="center", weight="bold")
        self.text(404.0, 9.6, self.scale, 2.2, ha="center")
        self.text(404.0, 3.3, self.no, 2.6, ha="center", weight="bold")

    def note(self, lines, size=1.5, legend=None):
        x0, y, x1, ybot = NOTE_BOX
        y -= 1.5
        for raw in lines:
            if raw == "":
                y -= size * 0.9
                continue
            bold = raw.startswith("#")
            s = raw.lstrip("# ")
            for i, ln in enumerate(wrap(s, x1 - x0 - (0 if bold or i == 0 else 2.5), size)):
                self.text(x0 + (0 if bold or i == 0 else 2.5), y, ln, size + (0.3 if bold else 0),
                          weight="bold" if bold else "normal", va="top")
                y -= size * 1.55
            y -= size * 0.35
        if legend:
            y -= 2
            for fc, hatch, label in legend:
                self.ax.add_patch(MPoly([(x0, y - 2.6), (x0 + 7, y - 2.6), (x0 + 7, y), (x0, y)], closed=True,
                                        fc=fc, ec="k", hatch=hatch, lw=D.LW["thin"] * D.PT, zorder=8))
                self.text(x0 + 9, y - 1.3, label, size)
                y -= 4.4
        disc = ["", "# 주의", "인허가·실시설계 검토용 초안입니다. 건축사·구조기술사의 검토와 날인 전에는 시공·제출에 쓰지 않습니다.",
                "치수 mm, 레벨 기준 GL±0 (설계 지반고)."]
        yd = ybot + 22
        if y > yd:
            for raw in disc:
                if raw == "":
                    continue
                bold = raw.startswith("#")
                for ln in wrap(raw.lstrip("# "), x1 - x0, 1.4):
                    self.text(x0, yd, ln, 1.4 + (0.3 if bold else 0), weight="bold" if bold else "normal",
                              va="top", color="#444444")
                    yd -= 2.2

    def heading(self, x, y, title, scale=None, num=None):
        if num:
            self.ax.add_patch(D.Circle((x + 3.2, y + 1.2), 3.2, fc="white", ec="k", lw=D.LW["vis"] * D.PT, zorder=7))
            self.text(x + 3.2, y + 1.2, num, 2.2, ha="center")
            x += 8
        self.text(x, y + 0.6, title, 3.2, weight="bold", va="bottom")
        self.hline(x, x + max(40, D.text_width(title, 3.2) + 4) if hasattr(D, "text_width") else x + 45, y - 0.2, "heavy")
        if scale:
            self.text(x, y - 1.4, f"SCALE {scale}", 1.8, va="top")

    def save(self):
        self.book.savefig(self.fig, transparent=True)
        D.plt.close(self.fig)


D.text_width = text_width

PLAN_NOTES = [
    "# 일반 사항",
    "1. 외벽: 스터코 10 + PF보드(준불연) 100 + RC 180 + 석고보드 9.5 (총 300)",
    "2. 내벽: 경량철골 칸막이 + 석고보드 9.5 2겹 양면 (THK150), 욕실·다용도실은 방수석고보드",
    "3. 창호 기호 W·D: A-001 창호일람표, AD: 내부 문",
    "4. 절단 높이 FL+1,200 위의 창은 점선",
    "5. 단면 표시 A-A' (A-401), B-B' (A-402)",
    "6. 치수: 외벽 바깥면·그리드(벽 중심선) 기준",
]
LEGEND = [(D.RC_FC, "////", "철근콘크리트"), (D.INS_FC, "....", "외단열 PF보드"), (D.PART_FC, "xx", "경량 칸막이")]


# ---------------------------------------------------------------- 시트
def cover(book):
    sh = FrameSheet(book, "A-000", "표지·건축개요", "NONE")
    sh.text(12, 284, S.PROJECT, 6.0, weight="bold")
    sh.text(12, 275, "인허가·실시설계 도서 (초안)  |  경일대학교 건축학부 " + COURSE, 2.6, color="#444444")
    img = HERE / "images" / "exterior.png"
    if img.exists():
        sh.ax.imshow(D.plt.imread(str(img)), extent=(12, 142, 160, 257.5), zorder=3)
    sh.heading(12, 148, "건축개요")
    rows = [("구분", "내용"), ("대지위치", "경상북도 경산시 진량읍 신제리·다문리 일원"),
            ("", "경산4일반산업단지 단독주택용지 (필지 미정)"), ("지역·지구", "제1종일반주거지역, 지구단위계획구역"),
            ("용도 / 구조", "단독주택 / 철근콘크리트 벽식구조, 박공지붕"),
            ("대지면적", f"{S.LOT_AREA:.2f}㎡"), ("건축면적", f"{S.BUILDING_AREA:.2f}㎡"),
            ("연면적", f"{S.GFA:.2f}㎡ (1층 {S.AREA_1F:.2f} / 2층 {S.AREA_2F:.2f})"),
            ("건폐율 / 용적률", f"{S.BUILDING_AREA / S.LOT_AREA:.2%} / {S.GFA / S.LOT_AREA:.2%}"),
            ("규모 / 높이", f"지상 2층 / {S.Z_TOP:.2f} m (층고 3.0 m)"),
            ("주차 / 조경", f"{len(S.PARKING)}대 / {S.LANDSCAPE:.2f}㎡"),
            ("단열 (U, W/㎡K)", f"외벽 {D.U_WALL:.3f} / 지붕 {D.U_ROOF:.3f} / 바닥 {D.U_FLOOR:.3f}")]
    sh.table(12, 140, [30, 100], rows, rh=6.6, size=1.9)
    sh.heading(155, 284, "도면 목록")
    sh.table(155, 276, [20, 70, 16], [("번호", "도면명", "축척")] + SHEETS, rh=5.8, size=1.8,
             aligns=["center", "left", "center"])
    sh.heading(155, 160, "법규 검토")
    rows = [("항목", "계획", "기준", "판정")] + [(n, val, lim, "적합" if ok else "부적합") for n, val, lim, ok, _ in ROWS]
    y = sh.table(155, 152, [18, 82, 68, 13], rows, rh=6.0, size=1.65)
    sh.text(155, y - 5, SUMMARY, 1.6, color="#444444")
    sh.note(["# 도서 구성", "A3 양식 출력 기준 축척입니다.", "평면·단면·지붕 1/50, 입면 1/100, 배치 1/200, 상세 1/20.",
             "", "# 기준 확인", "용도지역 기준값은 공개 자료 기준이며 해당 필지의 지구단위계획 결정도서로 확인이 필요합니다."])
    sh.save()


def schedules(book):
    sh = FrameSheet(book, "A-001", "면적표·창호·마감표", "NONE")
    sh.heading(12, 284, "면적표")
    rows = [("층", "바닥면적(㎡)", "용도"), ("1층", f"{S.AREA_1F:.2f}", "단독주택"), ("2층", f"{S.AREA_2F:.2f}", "단독주택"),
            ("합계", f"{S.GFA:.2f}", "")]
    y = sh.table(12, 276, [16, 28, 30], rows, rh=6.0, size=1.9, aligns=["center", "right", "center"])
    rows = [("층", "실명", "면적(㎡)")] + [(f"{r['floor']}층", r["name"], f"{S.room_area(r):.2f}") for r in S.ROOMS]
    sh.table(12, y - 6, [14, 34, 26], rows, rh=5.6, size=1.9, aligns=["center", "left", "right"])
    sh.heading(98, 284, "창호일람표")
    rows = [("기호", "층", "위치", "규격 W x H", "하단", "형식·사양")]
    for o in S.OPENINGS:
        rows.append((o["id"], f"{o['floor']}F", o["room"], f"{D.mm(o['a1'] - o['a0'])} x {D.mm(o['z1'] - o['z0'])}",
                     f"FL+{D.mm(o['z0'] - (S.FL1 if o['floor'] == 1 else S.FL2))}", o["spec"]))
    counts = {}
    for p in S.PARTS:
        for d in p["doors"]:
            if d[4] == "door":
                counts[d[5]] = counts.get(d[5], 0) + 1
    for k, (desc, w, h) in S.INNER_DOORS.items():
        rows.append((k, "1·2F", f"{counts.get(k, 0)}개소", f"{D.mm(w)} x {D.mm(h)}", "FL", desc))
    y = sh.table(98, 276, [13, 10, 18, 28, 17, 186], rows, rh=5.5, size=1.75,
                 aligns=["center", "center", "left", "center", "center", "left"])
    sh.heading(98, y - 10, "실내재료마감표")
    rows = [("층", "실명", "바닥", "걸레받이", "벽", "천장", "반자")]
    for r in S.ROOMS:
        f = r["fin"]
        rows.append((f"{r['floor']}F", r["name"], f[0], f[1], f[2], f[3], "-" if r["name"] == "테라스" else D.mm(S.CEIL_H)))
    sh.table(98, y - 18, [10, 18, 62, 32, 40, 66, 13], rows, rh=5.3, size=1.7,
             aligns=["center", "left", "left", "left", "left", "left", "center"])
    sh.note(["# 면적 산정", "바닥면적: 외벽 중심선 (외단열 포함 벽두께의 중심, 건축법 시행령 제119조)",
             "실면적: 마감면 기준 안목치수", "", "# 창호", "PVC 시스템창호, 24mm 삼중 로이유리, 단열간봉",
             "현관문: 단열 방화·방범문"])
    sh.save()


def site(book):
    sh = FrameSheet(book, "A-101", "배치도", "1/200")
    D.site_draw(sh, o=(62, 100), scale=200)
    sh.heading(30, 48, "배치도", "1/200")
    sh.north(160, 255)
    rows = [("항목", "내용"),
            ("대지위치", "경북 경산시 진량읍 신제리·다문리 일원"),
            ("", "경산4일반산업단지 단독주택용지 (필지 미정)"),
            ("지역·지구", "제1종일반주거지역, 지구단위계획구역"),
            ("대지면적", f"{S.LOT_AREA:.2f}㎡ ({D.mm(S.LOT_W)} x {D.mm(S.LOT_D)})"),
            ("건축면적", f"{S.BUILDING_AREA:.2f}㎡ (건폐율 {S.BUILDING_AREA / S.LOT_AREA:.2%})"),
            ("연면적", f"{S.GFA:.2f}㎡ (용적률 {S.GFA / S.LOT_AREA:.2%})"),
            ("규모·높이", f"지상 2층, 최고높이 {S.Z_TOP:.2f}m"),
            ("주차", f"{len(S.PARKING)}대 (법정 1대), 2.5 x 5.0 m"),
            ("조경", f"{S.LANDSCAPE:.2f}㎡ ({S.LANDSCAPE / S.LOT_AREA:.1%})"),
            ("이격거리", f"정북 {S.LOT_D - S.B1[3]:.1f} / 서 {S.B1[0]:.1f} / 동 {S.LOT_W - S.B1[2]:.1f} / 남 {S.B1[1]:.1f} m")]
    sh.table(190, 280, [26, 150], rows, rh=6.4, size=1.9)
    sh.note(["# 배치 사항", "필지 확정 후 지적측량 성과도로 대지 형상·면적·도로 폭을 다시 확인합니다.",
             "설계 지반고 GL±0 = 도로 경계 보도 상단 +150 (현황측량 후 확정).", "",
             "# 설비 인입", "오수: 분류식 공공하수관 직접 연결 (정화조 없음).",
             "우수: 선홈통 → 우수관 PE Ø150 → 도로측 우수 맨홀.", "", "# 외부",
             "생울타리 H1,200 (서·북·동), 주차 2대 일반형."])
    sh.save()


def plan(book, floor):
    sh = FrameSheet(book, f"A-20{floor}", f"{floor}층 평면도", "1/50")
    D.plan_draw(sh, floor, o=(73.2, 71.2))
    sh.heading(10, 44, f"{floor}층 평면도", "1/50", num=str(floor))
    lev = "1FL : GL+300" if floor == 1 else "2FL : GL+3,300"
    sh.text(18, 34, lev, 1.8)
    sh.text(18, 30, f"바닥면적 {(S.AREA_1F if floor == 1 else S.AREA_2F):.2f}㎡", 1.8)
    sh.north(362, 40, r=5)
    extra = (["7. 현관 바닥 FL-30, 화장실 FL-20 (구배 1/100)", "8. 계단 하부 수납장 (점검구 600x600)"] if floor == 1 else
             ["7. 계단 오픈부 난간 H1,200 (강관 + 강화유리)",
              "8. 테라스: 우레탄 도막방수, RD 루프드레인 Ø100, 파라펫 H1,200, 데크 +3,250"])
    sh.note(PLAN_NOTES + extra, legend=LEGEND)
    sh.save()


def roof(book):
    sh = FrameSheet(book, "A-203", "지붕 평면도", "1/50")
    D.roof_draw(sh, o=(73.2, 71.2))
    sh.heading(10, 44, "지붕 평면도", "1/50", num="3")
    sh.north(362, 40, r=5)
    sh.note(["# 일반 사항", "1. 지붕: 아스팔트 싱글 / 자착식 방수시트 / OSB 11 / 통기층 30 / PF보드 160 / RC 150",
             "2. 처마 하부 펀칭 소핏 → 용마루 벤트로 통기", "3. 처마홈통·선홈통: 알루미늄, 선홈통은 우수 맨홀로 연결",
             "4. 테라스 RD: 루프드레인 Ø100 + 오버플로 1개소", "5. 박공 끝 (동·서): 알루미늄 후레싱",
             "6. 처마 내밀기 500 (1 m 미만, 건축면적 불산입)"])
    sh.save()


ELEV_FIN = ["# 외부 마감", "1. 외벽: 스터코(준불연) 백색, 걸레받이 화강석 THK30 H300",
            "2. 지붕: 아스팔트 싱글 (흑회색), 처마 하부 알루미늄 소핏", "3. 창호: PVC 시스템창호 (회색), 삼중 로이유리",
            "4. 홈통: 알루미늄 처마홈통 W150, 선홈통 Ø100", "5. 테라스 파라펫: RC + 외단열, 알루미늄 두겁"]


def elevations(book, no, pair):
    names = {"S": "남측 입면도", "N": "북측 입면도", "E": "동측 입면도", "W": "서측 입면도"}
    nums = {"S": "1", "N": "2", "E": "3", "W": "4"}
    sh = FrameSheet(book, no, " · ".join(names[w] for w in pair), "1/100")
    for (which, y0, hy) in ((pair[0], 175, 152), (pair[1], 45, 22)):
        D.elevation_draw(sh, which, org=(27, y0), scale=100, notes_dx=58)
        sh.heading(12, hy, names[which], "1/100", num=nums[which])
    sh.note(ELEV_FIN)
    sh.save()


SECTION_NOTES = ["# 부위별 구성", "1. 지붕: 싱글 / 방수시트 / OSB 11 / 통기층 30 / PF보드 160 / RC 150",
                 "2. 외벽: 스터코 10 / PF보드 100 / RC 180 / 석고보드 9.5",
                 "3. 1층 바닥: 강마루 10 / 미장 50 / 기포 40 / XPS 특호 120 / PE필름 / 매트 400",
                 "4. 2층 바닥: 강마루 10 / 미장 40 / 기포 40 / RC 180",
                 "5. 테라스: 데크 / 보호몰탈 / 우레탄 도막방수 / PF보드 100 / RC 180",
                 "6. 기초: 매트 F1 THK400 + 외곽 기초보 FG1 (하단 GL-920)",
                 "7. 천장: 경량철골 천장틀 + 석고보드 9.5 2겹, 천장 내부 환기",
                 "8. 상세: A-501·A-502, 부재: S-001"]


def section(book, which):
    sh = FrameSheet(book, "A-401" if which == "A" else "A-402", f"단면도 {which}-{which}'", "1/50")
    D.section_draw(sh, which, o=(32, 40) if which == "A" else (24, 40))
    sh.heading(10, 22, f"단면도 {which}-{which}'", "1/50", num="1")
    key = "y = 11,000에서 북측을 봄" if which == "A" else "x = 11,650에서 서측을 봄 (계단 절단)"
    sh.text(80, 22, f"절단 위치: {key}", 1.8)
    sh.note(SECTION_NOTES)
    sh.save()


def details(book):
    sh = FrameSheet(book, "A-501", "상세 (기초·2층 바닥)", "1/20")
    D.detail_1(sh, (45, 180))
    sh.heading(12, 170, "상세 1  기초·외벽·1층 바닥", "1/20", num="1")
    D.detail_2(sh, (45, 42))
    sh.heading(12, 30, "상세 2  2층 바닥·외벽", "1/20", num="2")
    sh.note(["# 단열·방수", "외벽 PF보드(준불연) 100 외단열, 기초 외단열 XPS 50 + 도막방수 + 배수판.",
             "창 둘레 단열재는 끊기지 않게 프레임까지 붙입니다.", "", "# 철근", "부재 배근은 S-001 부재일람표 (예비 산정)."])
    sh.save()
    sh = FrameSheet(book, "A-502", "상세 (처마·테라스)", "1/20")
    D.detail_3(sh, (45, 185))
    sh.heading(12, 177, "상세 3  처마", "1/20", num="3")
    D.detail_4(sh, (45, 40))
    sh.heading(12, 26, "상세 4  테라스·파라펫", "1/20", num="4")
    sh.note(["# 통기·방수", "처마 소핏에서 용마루 벤트까지 통기층 30 연속.",
             "테라스 우레탄 도막방수는 파라펫·벽에 300 치켜올림, 문턱 방수턱 50.", "",
             "# 열교", "외벽 단열과 지붕 단열을 처마에서 연속시킵니다."])
    sh.save()


def structure(book):
    sh = FrameSheet(book, "S-001", "구조 일반사항·부재일람표", "NONE")
    sh.heading(12, 284, "구조 일반사항")
    gen = [
        "1. 설계기준: 건축구조기준 (KDS 41), 콘크리트구조 설계기준 (KDS 14 20)",
        f"2. 재료: 콘크리트 fck = {S.FCK} MPa, 철근 SD{S.FY} (D10~D22), 이음·정착은 KDS 14 20 52",
        "3. 하중: 고정하중은 실제 구성으로 산정, 활하중 주거 2.0 kN/㎡, 지붕 1.0 kN/㎡",
        "4. 적설·풍하중: 경산시 지역 기준값 (KDS 41 12 00) — 구조계산서에서 확정",
        "5. 내진: 2층 이상 → 구조안전 확인 대상 (건축법 시행령 제32조), 내진등급 II",
        "6. 지반: 허용지내력 fe ≥ 150 kN/㎡ 가정 — 지반조사(평판재하시험) 후 확정",
        "7. 피복두께: 흙에 접하는 기초 75, 흙에 접하는 벽 50, 실내 슬래브·벽 20, 보 40",
        "8. 개구부 보강: 개구부 둘레 2-D13, 모서리 사선보강 2-D13 (L=1,000)",
        "9. 부재 크기·배근은 예비 산정값이며 구조계산서와 구조기술사 검토로 확정한다.",
    ]
    for i, s_ in enumerate(gen):
        sh.text(14, 272 - i * 6.2, s_, 2.0)
    sh.heading(12, 205, "부재일람표")
    rows = [("부호", "부재", "크기", "배근", "비고")] + [tuple(m) for m in S.MEMBERS]
    sh.table(12, 197, [14, 32, 46, 86, 44], rows, rh=6.6, size=1.85)
    sh.heading(250, 205, "하중표 (kN/㎡, 추정)")
    lrows = [("부위", "고정", "활"), ("지붕 (경사)", "5.4", "1.0"), ("2층 바닥", "6.2", "2.0"),
             ("테라스", "7.0", "3.0"), ("계단", "6.5", "3.0")]
    sh.table(250, 197, [44, 28, 28], lrows, rh=6.6, size=1.9, aligns=["left", "center", "center"])
    sh.note(["# 구조 형식", "철근콘크리트 벽식구조 + 보 (G1, B1, TG1, RB1), 매트기초.", "",
             "# 확정 필요", "구조계산서, 지반조사, 지역 적설·풍하중."])
    sh.save()

    sh = FrameSheet(book, "S-101", "구조 평면도", "1/100")
    for kind, title, num, o, hd in (("F", "기초 구조평면도", "1", (31, 187), (14, 146)),
                                    ("2", "2층 바닥 구조평면도", "2", (206, 187), (189, 146)),
                                    ("R", "지붕 구조평면도", "3", (31, 43), (189, 128))):
        v = sh.view(*o, 100, u0=1.5, v0=9.0)
        D.struct_plan(v, kind)
        for name, g in S.GRID_X:
            v.line([(g, 7.4), (g, 17.6)], lw="fine", ls=(0, (12, 3, 2, 3)), color="#555555", z=1)
            v.bubble(g, 7.0, name, r=2.6)
        for name, g in S.GRID_Y:
            v.line([(0.4, g), (13.2, g)], lw="fine", ls=(0, (12, 3, 2, 3)), color="#555555", z=1)
            v.bubble(0.05, g, name, r=2.6)
        v.hdim([g for _, g in S.GRID_X], 6.2, size=1.6)
        v.hdim([1.5, 12.5], 5.6, size=1.7)
        sh.heading(*hd, title, "1/100", num=num)
    sh.text(189, 108, "범례", 2.4, weight="bold")
    sh.ax.add_patch(MPoly([(189, 98), (199, 98), (199, 102), (189, 102)], closed=True, fc=D.RC_FC, ec="k",
                          hatch="////", lw=D.LW["thin"] * D.PT, zorder=7))
    sh.text(202, 100, "W1 RC 내력벽 THK180 (해당 층 아래 벽)", 1.9)
    sh.ax.plot([189, 199], [92, 92], color="k", ls="--", lw=D.LW["vis"] * D.PT)
    sh.ax.plot([189, 199], [90, 90], color="k", ls="--", lw=D.LW["vis"] * D.PT)
    sh.text(202, 91, "보 (슬래브 아래)", 1.9)
    sh.note(["# 보", "TG1: 2층 서측 외벽(X2열)이 1층 거실 위에 놓이므로 전이보로 받친다.",
             "G1·B1: 2층 바닥 슬래브 경간을 5.7 m 이하로 나눈다.", "RB1: 동·서 박공벽에 걸친 용마루보.",
             "", "# 계단", "RC 계단 (경사판 THK150), 1층 바닥·참·2층 슬래브에 정착."])
    sh.save()


SHEETS = [
    ("A-000", "표지·건축개요·법규검토", "-"), ("A-001", "면적표·창호일람표·마감표", "-"),
    ("A-101", "배치도", "1/200"), ("A-201", "1층 평면도", "1/50"), ("A-202", "2층 평면도", "1/50"),
    ("A-203", "지붕 평면도", "1/50"), ("A-301", "남측·북측 입면도", "1/100"), ("A-302", "동측·서측 입면도", "1/100"),
    ("A-401", "단면도 A-A'", "1/50"), ("A-402", "단면도 B-B'", "1/50"), ("A-501", "상세 1·2 (기초, 2층 바닥)", "1/20"),
    ("A-502", "상세 3·4 (처마, 테라스)", "1/20"), ("S-001", "구조 일반사항·부재일람표", "-"),
    ("S-101", "구조 평면도", "1/100"),
]


def main():
    overlay = io.BytesIO()
    with PdfPages(overlay) as book:
        cover(book)
        schedules(book)
        site(book)
        plan(book, 1)
        plan(book, 2)
        roof(book)
        elevations(book, "A-301", "SN")
        elevations(book, "A-302", "EW")
        section(book, "A")
        section(book, "B")
        details(book)
        structure(book)
    overlay.seek(0)
    pages = PdfReader(overlay).pages
    writer = PdfWriter()
    for ov in pages:
        page = writer.add_page(PdfReader(TEMPLATE).pages[0])
        page.merge_page(ov)
    writer.add_metadata({"/Title": S.PROJECT + " 도면 (A3)", "/Author": DRAWN_BY})
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "wb") as f:
        writer.write(f)
    print(f"wrote {OUT} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
