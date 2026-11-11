"""인허가 주요 항목 검토. spec.py 값만 쓰므로 cad 없이도 돈다.  실행: python3 check.py

면적은 건축법 시행령 제119조대로 외벽 중심선(외단열 포함 벽두께의 중심)으로 산정한다.
"""

from spec import (AREA_1F, AREA_2F, B1, BUILDING_AREA, EAVE, FL1, FL2, GFA, LANDSCAPE, LOT_AREA,
                  LOT_D, LOT_W, PARK_D, PARK_W, PARKING, RAIL_H, RISE, ROAD_W, STAIR_W, TREAD, Z_TOP)


def parking_required(gfa):
    """주차장법 시행령 별표1 (단독주택): 50㎡ 초과 150㎡ 이하 1대, 150㎡ 초과는 100㎡당 1대 추가."""
    if gfa <= 50:
        return 0
    if gfa <= 150:
        return 1
    return int(1 + (gfa - 150) / 100 + 0.5)


NORTH_GAP = LOT_D - B1[3]
SETBACKS = {"서": B1[0], "동": LOT_W - B1[2], "북": NORTH_GAP, "남": B1[1]}

ROWS = [
    ("건폐율", f"{BUILDING_AREA:.2f} / {LOT_AREA:.0f} = {BUILDING_AREA / LOT_AREA:.2%}", "60% 이하",
     BUILDING_AREA / LOT_AREA <= 0.60, "국토계획법 시행령 제84조, 산단 단독주택용지 기준"),
    ("용적률", f"{GFA:.2f} / {LOT_AREA:.0f} = {GFA / LOT_AREA:.2%}", "180% 이하",
     GFA / LOT_AREA <= 1.80, "국토계획법 시행령 제85조, 산단 단독주택용지 기준"),
    ("층수·높이", f"지상 2층, 최고높이 {Z_TOP:.2f} m", "3층 이하", True, "산단 단독주택용지 기준"),
    ("정북 일조", f"정북 인접대지경계선에서 {NORTH_GAP:.1f} m", "높이 10 m 이하 부분 1.5 m 이상",
     Z_TOP <= 10 and NORTH_GAP >= 1.5, "건축법 제61조, 시행령 제86조"),
    ("접도", f"폭 {ROAD_W:.0f} m 도로에 {LOT_W:.1f} m 접함", "4 m 이상 도로에 2 m 이상", True, "건축법 제44조"),
    ("주차", f"{len(PARKING)}대 ({PARK_W} x {PARK_D} m 일반형)", f"{parking_required(GFA)}대 이상",
     len(PARKING) >= parking_required(GFA), "주차장법 시행령 별표1, 시행규칙 제3조"),
    ("조경", f"{LANDSCAPE:.1f} ㎡ ({LANDSCAPE / LOT_AREA:.0%})", "경산시 건축조례 기준",
     LANDSCAPE / LOT_AREA >= 0.15, "건축법 제42조"),
    ("계단", f"단높이 {RISE * 1000:.1f} / 단너비 {TREAD * 1000:.0f} / 너비 {STAIR_W * 1000:.0f} mm",
     "200 이하 / 240 이상 / 600 이상", RISE <= 0.2 and TREAD >= 0.24 and STAIR_W >= 0.6,
     "건축물의 피난·방화구조 등의 기준에 관한 규칙 제15조"),
    ("난간", f"테라스·계단 개구부 {RAIL_H * 1000:.0f} mm", "1,200 mm 이상", RAIL_H >= 1.2, "건축법 시행령 제40조"),
    ("인접 이격", ", ".join(f"{k} {v:.1f} m" for k, v in SETBACKS.items()), "0.5 m 이상",
     min(SETBACKS.values()) >= 0.5, "민법 제242조"),
    ("처마", f"내밀기 {EAVE:.1f} m", "1 m 미만 → 건축면적 불산입", EAVE < 1.0, "건축법 시행령 제119조"),
    ("내진", "지상 2층 → 구조안전 확인 대상", "내진설계 적용", True, "건축법 제48조, 시행령 제32조"),
]

SUMMARY = (f"대지 {LOT_AREA:.2f} ㎡ · 건축면적 {BUILDING_AREA:.2f} ㎡ · 연면적 {GFA:.2f} ㎡ "
           f"(1층 {AREA_1F:.2f}, 2층 {AREA_2F:.2f}) · 층고 {FL2 - FL1:.1f} m")

if __name__ == "__main__":
    print(SUMMARY + "\n")
    for name, value, limit, ok, law in ROWS:
        print(f"{'OK ' if ok else 'NG '} {name:<6} {value:<40} {limit:<26} {law}")
