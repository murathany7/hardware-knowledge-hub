"""Tight splash-proof shell for one AJ-SR04M ultrasonic control board (the probe itself is separate, on its own cable).
Two plates: the shells next to each other, and their lids.

Run:  python hardware/cad/ultrasonic_box.py [--out hardware/cad/out] [--tag v1] [--count N]
The numbers live in parameters.json (groups "Ultrasonic ..."), editable in the editor: python3 hardware/knowledge/kb.py serve.

Frame: Y along the board, X across it, Z up from the outside of the floor. The board lies component side up on four posts with pins
through its corner holes; the lid has pegs that press it down. No empty space: the cavity is the board plus 0.4 mm. The Dupont plugs
are NOT used: the four wires are soldered to the header and leave straight out through a notch, open at the top, in the +X long wall.
The probe cable goes straight down through a hole in the exact centre of the floor; a short dent in the floor lets the plug sink in.
No screws: the lid has a lip that presses into the opening, sealed with silicone (also in the notch and the cable hole). Printed ASA
is not guaranteed watertight: use the bath test in PROJECT.md before riding.
"""
import argparse
import json
import os
import pathlib

import cadquery as cq

# ----------------------------------------------------------------------------- PARAMETERS (mm)
P = {p["key"]: p["value"] for p in json.loads(pathlib.Path(__file__).with_name("parameters.json").read_text())["parameters"]}
BX, BY, BT = P["US_BX"], P["US_BY"], P["US_BT"]          # board outline and thickness (ESTIMATES)
HDX, HDY, HD = P["US_HDX"], P["US_HDY"], P["US_HD"]      # corner hole spacing and diameter (ESTIMATES)
BACK_H, TOP_H = P["US_BACK_H"], P["US_TOP_H"]            # parts under / over the board
PLUG_OVER, DUP_LEN = P["US_PLUG_OVER"], P["US_DUP_LEN"]  # corridor at the -X end, room beside the header edge
COUNT = int(P["US_COUNT"])
FL, WALL, GW, GD, LID_T = P["US_FL"], P["US_WALL"], P["US_GW"], P["US_GD"], P["US_LID_T"]
PROBE_D, WIRE_D, STANDOFF = P["US_PROBE_D"], P["US_WIRE_D"], P["US_STANDOFF"]   # probe cable hole (floor), wire hole (end wall), board height above the floor
TIE_W, TIE_T = P["US_TIE_W"], P["US_TIE_T"]
FIT, E = 0.4, 1.0                                        # clearance per side, boolean overshoot
PLUG_Z = 12.5                                            # probe plug centre this far in from the header edge (ESTIMATE from the photo)
POST_R = 3.0                                             # board post radius
PEG_D, PEG_GAP = 3.4, 0.3                                # lid pegs that press the board onto its posts, gap to the board
LIP, LIP_FIT = 3.0, 0.15                                 # lid lip that presses into the opening: height, clearance per side
# ----------------------------------------------------------------------------- derived
# Frame: the cable leaves the plug at the -Y end of the board (x = 0). The board lies with its long side along Y, header edge
# towards +X. The cavity is sized tightly round the board and the wire corridor, and the probe cable hole is in its exact centre.
RIM = WALL                                                     # one plain wall, lid sealed with silicone
Y0 = -1.0                                                      # -Y end of the board
XB = PLUG_Z - BY / 2                                           # board centre in X: puts the plug cable on x = 0 (the header edge is at x = +PLUG_Z)
YB = Y0 + BX / 2                                               # board centre in Y
XMIN, XMAX = XB - BY / 2 - FIT, XB + BY / 2 + FIT + DUP_LEN
YMIN, YMAX = Y0 - FIT - PLUG_OVER, Y0 + BX + FIT
CX, CY = XMAX - XMIN, YMAX - YMIN                              # cavity
CXM, CYM = (XMIN + XMAX) / 2, (YMIN + YMAX) / 2                # cavity centre
XH, YH = CXM, CYM                                              # the probe cable goes down through the floor at the exact centre of the box
CZ = STANDOFF + BT + TOP_H + 1.0 + LIP
H = FL + CZ                                                    # housing height, the lid sits on top
XO, YO = CX / 2 + RIM, CY / 2 + RIM
ZU = FL + STANDOFF                                             # underside of the board
ZT = ZU + BT
HOLES = [(XB + sx * HDY / 2, YB + sy * HDX / 2) for sx in (-1, 1) for sy in (-1, 1)]
CABLE_Z, WIRE_Z = ZU - BACK_H / 2, ZT + 3.5                    # probe cable level on the board, Dupont wire level
DENT_Y0, DENT_Y1, DENT_W = min(YH - PROBE_D / 2, Y0 + 1.3), max(Y0 + 4.3 + 18.0 + 1.0, YH + PROBE_D / 2 + 1.0), 11.0   # floor dent for the plug: from the cable exit to past the socket and the centre hole
DENT_D = BACK_H - STANDOFF + 1.0                               # deep enough for the plug to sink into
NOTCH_Z = WIRE_Z - 2.5                                         # bottom of the wire notch in the +X wall
TIES = (DENT_Y1 + 5.0, DENT_Y1 + 16.0)                         # y of the two zip-tie tunnels, clear of the plug dent


def vol(s):
    return s.val().Volume() if s.vals() else 0.0


def blk(x, y, z, cx, cy, z0):
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, False)).translate((cx, cy, z0))


def cyl(r, z0, z1, cx, cy):
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((cx, cy, z0))


def ycyl(r, y0, y1, cx, cz):
    return cq.Workplane("XY").circle(r).extrude(y1 - y0).rotate((0, 0, 0), (1, 0, 0), -90).translate((cx, y0, cz))


def xcyl(r, x0, x1, y, z):
    return cq.Workplane("YZ").circle(r).extrude(x1 - x0).translate((x0, y, z))


def rrect(w, d, r, z0, z1):
    s = blk(w - 2 * r, d, z1 - z0, 0, 0, z0).union(blk(w, d - 2 * r, z1 - z0, 0, 0, z0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            s = s.union(cyl(r, z0, z1, sx * (w / 2 - r), sy * (d / 2 - r)))
    return s


def outline(z0, z1):
    return rrect(2 * XO, 2 * YO, 3.0, z0, z1).translate((CXM, CYM, 0))


def build_housing():
    h = outline(0, H).cut(blk(CX, CY, CZ + E, CXM, CYM, FL))                       # cavity
    for x, y in HOLES:                                                         # board posts with locating pins
        h = h.union(cyl(POST_R, FL - E, ZU, x, y)).union(cyl(HD / 2 - 0.2, ZU, ZT, x, y))
    h = h.cut(blk(DENT_W, DENT_Y1 - DENT_Y0, DENT_D + E, 0.0, (DENT_Y0 + DENT_Y1) / 2, FL - DENT_D))     # short dent in the floor for the plug
    h = h.cut(cyl(PROBE_D / 2, -E, FL, XH, YH))                                # probe cable straight down through the exact centre of the floor
    h = h.cut(blk(RIM + 2 * E, WIRE_D, H - NOTCH_Z + E, CXM + CX / 2 + RIM / 2, YB, NOTCH_Z))   # wire notch: open from the top, in the +X wall at the header
    for ty in TIES:                                                            # zip-tie tunnels under the floor, across the box
        h = h.cut(blk(2 * XO + 2 * E, TIE_W, TIE_T, CXM, ty, 2.0))
    return h


def build_lid():
    lid = outline(H, H + LID_T)
    plug = rrect(CX - 2 * LIP_FIT, CY - 2 * LIP_FIT, 3.0, H - LIP, H + E).translate((CXM, CYM, 0))     # lip that presses into the opening
    plug = plug.cut(blk(RIM + 2 * E, WIRE_D, LIP + 2 * E, CXM + CX / 2 + RIM / 2, YB, H - LIP - E))    # clear of the wires
    lid = lid.union(plug)
    for x, y in HOLES:
        lid = lid.union(cyl(PEG_D / 2, ZT + PEG_GAP, H + E, x, y))
    return lid


# ----------------------------------------------------------------------------- fit-check dummies
def board_dummy():
    pcb = blk(BY, BX, BT, XB, YB, ZU)
    for x, y in HOLES:
        pcb = pcb.cut(cyl(HD / 2, ZU - E, ZT + E, x, y))
    # probe socket in the middle of the back (about 19-22 mm from the cable end in the photo), the black plug runs from it
    # towards the -Y end (positions ESTIMATED from the photo)
    plug = blk(8.0, 18.0, BACK_H - 1.0, 0.0, Y0 + 4.3 + 9.0, ZU - BACK_H + 1.0)
    hdr = blk(3.0, 11.0, 2.5, PLUG_Z - 1.5, YB, ZT)                                                  # header pins with the soldered wires (no plugs)
    top = blk(BY - 8.5, BX - 10.0, TOP_H - 2.0, XB, YB, ZT)                                         # chips and capacitors
    return pcb.union(plug).union(hdr).union(top)


def cables_dummy():
    """Where the cables run: the probe cable from its plug down through the floor; the soldered wires from the header straight out
    through the notch in the +X wall."""
    cable = cyl(2.0, -E, FL, XH, YH)                                                                 # the probe cable inside its hole; in the dent it runs from the plug end to here
    wires = blk(XMAX + RIM + 4.0 - PLUG_Z, WIRE_D - 3.0, 3.0, (PLUG_Z + XMAX + RIM + 4.0) / 2, YB, WIRE_Z - 1.5)   # soldered wires out through the notch
    return cable.union(wires)


def checks(housing, lid):
    brd, cab = board_dummy(), cables_dummy()
    for name, s in (("housing", housing), ("lid", lid)):
        b = s.val().BoundingBox()
        print(f"{name:<8} vol {vol(s):7.0f} mm3  solids {s.solids().size()}  valid {s.val().isValid()}  "
              f"{b.xlen:.1f} x {b.ylen:.1f} x {b.zlen:.1f}")
        assert s.solids().size() == 1 and s.val().isValid(), f"{name} is not one valid solid"
    assert vol(housing.intersect(brd)) < 0.01, "housing clashes with the board"
    assert vol(lid.intersect(brd)) < 0.01, "lid clashes with the board"
    assert vol(housing.intersect(lid)) < 0.01, "lid overlaps housing"
    assert vol(housing.intersect(cab)) < 0.01, "a cable runs into a post, a wall or the floor"
    assert TIE_T + 2.0 <= FL - 2.0, "tie tunnel leaves under 2 mm of floor above it"
    assert NOTCH_Z > FL + 1.0 and WIRE_D < CY, "wire notch reaches the floor or is wider than the wall"
    assert FL - DENT_D >= 2.5, "the dent leaves under 2.5 mm of floor"
    for ty in TIES:
        assert vol(blk(2 * XO, TIE_W, TIE_T, CXM, ty, 2.0).intersect(blk(DENT_W + 2, DENT_Y1 - DENT_Y0 + 2, FL, 0, (DENT_Y0 + DENT_Y1) / 2, 0))) < 0.01, "a zip-tie tunnel runs under the plug dent or the probe cable hole"
    print(f"box {2 * XO:.1f} x {2 * YO:.1f} x {H + LID_T:.1f} mm; probe cable down through the floor ({PROBE_D:.0f} mm hole, in the exact centre of the floor, dent {DENT_D:.0f} mm deep), "
          f"wire notch {WIRE_D:.0f} mm wide, open at the top, in the +X wall at the header; no screws")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "out"))
    ap.add_argument("--tag", default="")
    ap.add_argument("--count", type=int, default=COUNT, help="boxes on the plate")
    a = ap.parse_args()
    import trimesh
    from plate3mf import export_3mf
    os.makedirs(a.out, exist_ok=True)
    housing, lid = build_housing(), build_lid()
    checks(housing, lid)
    tag = "_" + a.tag if a.tag else ""

    def f(n, ext):
        return os.path.join(a.out, n + tag + ext)
    lp = lid.rotate((0, 0, 0), (1, 0, 0), 180)                      # lid outer face down, pegs up
    for n, s in (("ultrasonic_box", housing), ("ultrasonic_lid", lp)):
        s = s.translate((0, 0, -s.val().BoundingBox().zmin))
        cq.exporters.export(s, f(n, ".step"))
        cq.exporters.export(s, f(n, ".stl"), tolerance=0.02)

    def put(m, x, y):
        m = m.copy()
        c = m.bounds.mean(axis=0)
        m.apply_translation([x - c[0], y - c[1], -m.bounds[0][2]])
        return m
    box, cover = trimesh.load(f("ultrasonic_box", ".stl")), trimesh.load(f("ultrasonic_lid", ".stl"))
    w, d = 2 * XO + 4.0, 2 * YO + 4.0          # footprint of one part with a gap
    cols = max(1, min(a.count, int(246 // w)))
    rows = -(-a.count // cols)
    assert rows * d <= 246, f"{a.count} parts do not fit on the 256 mm plate: print fewer per plate"
    for plate, kind, model in (("ultrasonic_boxes_plate", "box", box), ("ultrasonic_lids_plate", "lid", cover)):   # boxes and lids on two plates
        parts = {}
        for n in range(a.count):
            r, c = divmod(n, cols)
            parts[f"ultrasonic_{kind}_{n + 1}"] = put(model, (c - (cols - 1) / 2) * w, (r - (rows - 1) / 2) * d)
        export_3mf(parts, f(plate, ".3mf"))
        trimesh.util.concatenate(list(parts.values())).export(f(plate, ".stl"))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
