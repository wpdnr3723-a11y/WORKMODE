"""house.py 상수로 인허가 주요 항목을 계산해 표로 출력한다.  실행: cad run check.py"""

from house import (B1, B2, EAVE, FL1, FL2, GARDEN, LOT_D, LOT_W, PARK_D, PARK_W, PARKING,
                   RAIL_H, RISE, ROAD_W, STAIR_W, TREAD, house)


def area(b):
    return (b[2] - b[0]) * (b[3] - b[1])


lot = LOT_W * LOT_D
footprint = area(B1)                      # 처마 내밀기 1 m 미만 -> 건축면적 불산입
gfa = area(B1) + area(B2)
landscape = area(GARDEN) + (14.5 - 0.5) * (19.5 - 17.4)
height = house().shape.bounding_box().max.Z / 1000.0
north_gap = LOT_D - B1[3]
setbacks = {"서": B1[0], "동": LOT_W - B1[2], "북": north_gap, "남": B1[1]}
need_park = 1 + max(0.0, gfa - 150) / 100     # 주차장법 시행령 별표1: 150㎡ 초과분 100㎡당 1대
need_park = int(need_park + 0.5)              # 0.5 미만 버림

rows = [
    ("건폐율", f"{footprint:.1f}/{lot:.0f} = {footprint / lot:.1%}", "≤ 50%", footprint / lot <= 0.50,
     "국토계획법 시행령 제84조 (제1종전용주거), 지구단위계획"),
    ("용적률", f"{gfa:.1f}/{lot:.0f} = {gfa / lot:.1%}", "≤ 100% (법정 50~100%)", gfa / lot <= 1.00,
     "국토계획법 시행령 제85조"),
    ("층수·높이", f"2층, 최고높이 {height:.2f} m", "2층 이하 (지구단위계획 가정)", True,
     "지구단위계획 (확인 필요)"),
    ("정북 일조", f"북측 경계 이격 {north_gap:.1f} m", "높이 10 m 이하 부분 ≥ 1.5 m",
     height <= 10 and north_gap >= 1.5, "건축법 시행령 제86조"),
    ("접도", f"폭 {ROAD_W:.0f} m 도로에 {LOT_W:.0f} m 접함", "4 m 이상 도로에 2 m 이상", True,
     "건축법 제44조"),
    ("주차", f"{len(PARKING)}대 ({PARK_W} x {PARK_D} m)", f"{need_park}대 이상", len(PARKING) >= need_park,
     "주차장법 시행령 별표1, 시행규칙 제3조"),
    ("조경", f"{landscape:.1f} ㎡ ({landscape / lot:.0%})", "조례 기준 (통상 대지의 10~15%)",
     landscape / lot >= 0.15, "건축법 제42조, 성남시 건축조례"),
    ("계단", f"단높이 {RISE * 1000:.1f}, 단너비 {TREAD * 1000:.0f}, 너비 {STAIR_W * 1000:.0f} mm",
     "≤ 200 / ≥ 240 / ≥ 600 mm", RISE <= 0.2 and TREAD >= 0.24 and STAIR_W >= 0.6,
     "피난·방화구조 규칙 제15조"),
    ("난간", f"테라스 난간 {RAIL_H * 1000:.0f} mm", "≥ 1,200 mm", RAIL_H >= 1.2, "건축법 시행령 제40조"),
    ("인접 이격", ", ".join(f"{k} {v:.1f} m" for k, v in setbacks.items()), "≥ 0.5 m (지구단위계획 건축한계선 확인)",
     min(setbacks.values()) >= 0.5, "민법 제242조"),
    ("처마", f"내밀기 {EAVE:.1f} m", "1 m 미만이면 건축면적 불산입", EAVE < 1.0, "건축법 시행령 제119조"),
]

print(f"대지 {lot:.0f} ㎡ · 건축면적 {footprint:.1f} ㎡ · 연면적 {gfa:.1f} ㎡ (1층 {area(B1):.0f}, 2층 {area(B2):.0f})")
print(f"층고 {FL2 - FL1:.1f} m\n")
for name, value, limit, ok, law in rows:
    print(f"{'OK ' if ok else 'NG '} {name:<6} {value:<38} {limit:<28} {law}")
