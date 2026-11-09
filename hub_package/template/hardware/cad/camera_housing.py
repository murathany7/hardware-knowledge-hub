"""Waterproof housing for the rear camera (Raspberry Pi Camera Module 3 Wide) of the bike logger, clamped to the
back end of the rear rack (the round tube that runs sideways behind the main box).

Run:  python hardware/cad/camera_housing.py [--out hardware/cad/out] [--tag v1]
Change the numbers in parameters.json (or in the editor), run again, print the plate. Everything is derived from them.

Frame (housing): X across the housing (along the rack tube), Z up, Y from the front face (y = 0, the camera looks
towards -Y, i.e. backwards on the bike) to the open back at y = D, which the lid closes. Origin x = 0 / z = 0 is the
centre of the cavity. The board sits ribbon-down, connector at the bottom edge (the usual way up for a Pi camera): the
flat ribbon leaves the connector straight down and goes out through a slot in the floor right under it, with no bend
inside the housing.

Mount: a block on top of the housing has a 90 degree V along X; the rack tube (wrapped in a strip of inner tube) lies in
it and a printed cap with a round groove is pulled down by two M3 screws into heat-set inserts. The housing hangs under
the tube and can be turned round it to aim the camera before the screws are tightened.

Waterproofing, in the order water would meet it:
  1. Window: a flat piece of clear plastic (cut from the clear lid of the spare 115 x 90 x 55 mm box) sits in a
     recess in the outside of the front wall and is bonded with silicone. Water pressure pushes it onto its seat.
     The lens barrel reaches into the front wall so the glass sits 0.5 mm behind the window (the Wide lens sees
     120 degrees diagonally; a window further away would show its own edges).
  2. Lid: a 3 mm silicone foam cord lies in a groove in the housing rim. The lid goes straight on (its four pegs press
     the board onto its posts, a lip keeps it square) and two lock bars hold it, with nothing that flexes (printed
     snap arms fatigue and crack): each side of the housing has a solid rail and the lid a flange beside it; a rigid
     C-shaped bar slides down from the top over rail and flange together. The rail's front face tapers by TAPER over
     its length, so the bar pulls the lid onto the cord as it goes down; the slope is far too shallow to back out,
     and the housing hangs, so gravity keeps the bars down. To open, pull the bars up by their heads.
  3. Cable: the flat camera ribbon leaves straight down through a slot in the floor, in line with the connector, in a
     glue-lined heat-shrink sleeve, and the slot is filled with silicone. It faces the ground, so water runs off it.
  4. The clamp inserts are blind (they never open into the cavity).
Printed ASA cannot be promised watertight on its own: print with 4+ walls and do the bath test.
"""
import argparse
import json
import math
import os
import pathlib

import cadquery as cq

# ----------------------------------------------------------------------------- PARAMETERS (mm)
# The numbers live in parameters.json (keys C_..., groups "Camera board (Module 3 Wide)", "Camera housing" and
# "Camera rack clamp"), editable in the editor: python3 hardware/knowledge/kb.py serve
P = {p["key"][2:]: p["value"] for p in json.loads(pathlib.Path(__file__).with_name("parameters.json").read_text())["parameters"]
     if p["key"].startswith("C_")}
# Camera Module 3 Wide, from the official Raspberry Pi mechanical drawing
CAM_W, CAM_H, CAM_T = P["CAM_W"], P["CAM_H"], P["CAM_T"]          # board width (X), height (Z), PCB thickness
HOLE_DX, HOLE_DZ, HOLE_Z0 = P["HOLE_DX"], P["HOLE_DZ"], P["HOLE_Z0"]   # hole spacing X and Z, lower holes above the bottom edge
HOLE_D, PAD_D = P["HOLE_D"], P["PAD_D"]           # hole and copper pad diameter
LENS_X, LENS_Z0 = P["LENS_X"], P["LENS_Z0"]       # lens centre: from the board's centre line, from the board's bottom edge
LENS_W, LENS_H = P["LENS_W"], P["LENS_H"]         # square lens block: footprint, height above the PCB
LENS_TOP, NOSE_D = P["LENS_TOP"], P["NOSE_D"]     # PCB front to lens tip, round barrel diameter
DEPTH_ALL = P["DEPTH_ALL"]                        # lens tip to back of connector
CONN_W, CONN_H = P["CONN_W"], P["CONN_H"]         # ribbon connector on the back, at the top edge
FOV_D, GLASS_D = P["FOV_D"], P["GLASS_D"]         # diagonal field of view (deg), front glass diameter (estimate)
# housing
FIT, E = 0.4, 1.0                                 # clearance per side, boolean overshoot
CAV_GAP, RIB_ROOM, BACK_ROOM = P["CAV_GAP"], P["RIB_ROOM"], P["BACK_ROOM"]   # room round the board, under it, behind the connector
LG, BLOCK_GAP = P["LG"], P["BLOCK_GAP"]           # lens tip to window, lens block to front wall
WALL, GROOVE_W, GROOVE_D, CORD = P["WALL"], P["GROOVE_W"], P["GROOVE_D"], P["CORD"]   # wall each side of the gasket groove, groove, foam cord
CORNER, GROOVE_R, POST_R = P["CORNER"], P["GROOVE_R"], P["POST_R"]   # outer corner radius, groove outer corner radius, PCB post radius
WIN, WIN_T, WIN_RECESS = P["WIN"], P["WIN_T"], P["WIN_RECESS"]       # square window plate, thickness, recess in the outside of the front wall
INS_D, INS_DEEP, CLR_D = P["INS_D"], P["INS_DEEP"], P["CLR_D"]   # M3 inserts and clearance holes (clamp)
LID_T, PEG_D, PEG_GAP = P["LID_T"], P["PEG_D"], P["PEG_GAP"]         # lid, pegs that press the PCB onto its posts
LIP_H, LIP_T = P["LIP_H"], P["LIP_T"]             # locating lip on the lid, inside the cavity
FL, FT, TAPER = P["FL"], P["FT"], P["TAPER"]      # side rail: out from the wall (X), thickness (Y), taper of its front face
BAR_T, HEAD, SL_GAP, SL_PLAY = P["BAR_T"], P["HEAD"], P["SL_GAP"], P["SL_PLAY"]   # lock bar wall, head, clearance, play
SLOT_W, SLOT_T, RIB_W = P["SLOT_W"], P["SLOT_T"], P["RIB_W"]   # ribbon slot in the floor (X, Y), ribbon width
# rack clamp
RACK_D, RACK_PAD, TUBE_UP = P["RACK_D"], P["RACK_PAD"], P["TUBE_UP"]   # rack tube (ESTIMATE), rubber pad, tube centre above the block top
CAP_GAP, CAP_L, CAP_TOP = P["CAP_GAP"], P["CAP_L"], P["CAP_TOP"]       # cap-to-block gap, cap length along the tube, cap over the tube
HEAD_D, UNDER_HEAD, SCREW_EDGE = P["HEAD_D"], P["UNDER_HEAD"], P["SCREW_EDGE"]
# ----------------------------------------------------------------------------- derived
NOSE_L = LENS_TOP - LENS_H              # round barrel on top of the square block
BACK_H = DEPTH_ALL - LENS_TOP - CAM_T   # behind the PCB (the connector)
RIM = 2 * WALL + GROOVE_W               # wall around the cavity (6.4)
CX, CZ = CAM_W + 2 * CAV_GAP, CAM_H + CAV_GAP + RIB_ROOM   # cavity width (X) and height (Z)
BZ1 = CZ / 2 - CAV_GAP                  # ribbon down: the drawing's bottom edge (lens side) is at the top
BZ0 = BZ1 - CAM_H                       # connector edge, RIB_ROOM above the floor
LENS_Z, LENS_XH = BZ1 - LENS_Z0, -LENS_X   # drawing z and x both flip (drawing is ribbon-up)
FW = WIN_RECESS + LG + NOSE_L - BLOCK_GAP   # front wall: lens tip LG behind the window, block BLOCK_GAP off the wall
PCB_Y0 = FW + BLOCK_GAP + LENS_H        # front face of the PCB (= top of the posts)
PCB_Y1 = PCB_Y0 + CAM_T
HOLES = [(sx * HOLE_DX / 2, BZ1 - HOLE_Z0 - dz) for sx in (-1, 1) for dz in (0.0, HOLE_DZ)]
XO = CX / 2 + RIM                       # outer half width
ZT, ZB = CZ / 2 + RIM, -(CZ / 2 + RIM)  # outer top and bottom of the body
# clamp: tube of radius R (with pad) in a 90 degree V; block top BT, tube centre ZC
R = RACK_D / 2 + RACK_PAD
V_HW = R * math.sqrt(2) - TUBE_UP       # half width of the V at the block top
MB_T = max(0.0, V_HW + 2.0 - RIM, INS_DEEP + 1.0 - RIM)   # block above the body: 2 mm under the V, 1 mm under the inserts
BT = ZT + MB_T
ZC = BT + TUBE_UP
CAP_Z0 = BT + CAP_GAP                   # underside of the cap
CAP_HW = math.sqrt(max(R * R - (ZC - CAP_Z0) ** 2, 0.0))   # half width of the cap's round groove at its underside
SD = max(V_HW + INS_D / 2, CAP_HW + CLR_D / 2) + SCREW_EDGE   # screw centres either side of the tube (Y)
YC = WALL + INS_D / 2 + SD              # tube centre (Y): front insert 1.6 mm from the front face
D = max(PCB_Y1 + BACK_H + BACK_ROOM,    # housing depth: the camera, or the clamp with its rear insert clear of the gasket groove
        YC + SD + INS_D / 2 + GROOVE_D + 1.5)
CAP_W = 2 * (SD + HEAD_D / 2 + 1.6)     # cap size across the tube (Y)
CAP_ZT = ZC + R + CAP_TOP               # top of the cap
RIB_Y = PCB_Y1 + BACK_H / 2            # the ribbon leaves the connector half way up its height behind the PCB
ZF = ZT - CORNER                        # rails, flanges and bars run along the flat part of the sides, z = -ZF..ZF
XB0 = XO + FL + SL_GAP                  # inner face of the lock bar's back
XB1 = XB0 + BAR_T                       # outer face of the bar
YB0 = D - FT - TAPER - SL_PLAY - BAR_T  # front face of the bar
YB1 = D + LID_T + BAR_T                 # back face of the bar
SCREWS = [(0.0, YC + sy * SD) for sy in (-1, 1)]   # clamp screws (x, y)


def vol(s):
    return s.val().Volume() if s.vals() else 0.0


def prism(w, h, y0, y1, cx=0.0, cz=0.0):   # box in X/Z, along Y from y0 to y1
    return cq.Workplane("XY").box(w, y1 - y0, h).translate((cx, (y0 + y1) / 2, cz))


def ycyl(r, y0, y1, cx, cz):
    return cq.Workplane("XY").circle(r).extrude(y1 - y0).rotate((0, 0, 0), (1, 0, 0), -90).translate((cx, y0, cz))


def zcyl(r, z0, z1, cx, cy):
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((cx, cy, z0))


def xcyl(r, x0, x1, cy, cz):
    return cq.Workplane("YZ").circle(r).extrude(x1 - x0).translate((x0, cy, cz))


def rrect_xz(w, h, r, y0, y1, cx, cz):     # rounded rectangle in X/Z extruded along Y
    s = prism(w - 2 * r, h, y0, y1, cx, cz).union(prism(w, h - 2 * r, y0, y1, cx, cz))
    for sx in (-1, 1):
        for sz in (-1, 1):
            s = s.union(ycyl(r, y0, y1, cx + sx * (w / 2 - r), cz + sz * (h / 2 - r)))
    return s


def outline(y0, y1):
    return rrect_xz(2 * XO, ZT - ZB, CORNER, y0, y1, 0, 0)


def yz_prism(pts, x0, x1):                # polygon in (y, z) extruded along X from x0 to x1
    return cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0).translate((x0, 0, 0))


def side_x(sx, a, b):                      # X range from |x| = a to b on side sx
    return (a, b) if sx > 0 else (-b, -a)


def rail_front(z):                         # the rail's front face: thicker towards the bottom, so the bar wedges on
    return D - FT - TAPER * (ZF - z) / (2 * ZF)


def rail(sx):                              # solid rail on the outside of the side wall, next to the lid
    x0, x1 = side_x(sx, XO - E, XO + FL)
    return yz_prism([(rail_front(ZF), ZF), (D, ZF), (D, -ZF), (rail_front(-ZF), -ZF)], x0, x1)


def build_bar(sx=1):                       # rigid C over rail and lid flange; head on top rests on them
    x0, x1 = side_x(sx, XO + SL_GAP, XB1)
    bar = prism(x1 - x0, 2 * ZF + HEAD, YB0, YB1, (x0 + x1) / 2, HEAD / 2)
    c0, c1 = side_x(sx, XO + SL_GAP - E, XB0)
    lo = -ZF - E
    return bar.cut(yz_prism([(rail_front(ZF) - SL_PLAY, ZF), (D + LID_T, ZF), (D + LID_T, lo),
                             (rail_front(lo) - SL_PLAY, lo)], c0, c1))


def groove_ring():
    a = rrect_xz(CX + 2 * (WALL + GROOVE_W), CZ + 2 * (WALL + GROOVE_W), GROOVE_R, D - GROOVE_D, D + E, 0, 0)
    b = rrect_xz(CX + 2 * WALL, CZ + 2 * WALL, CORNER, D - GROOVE_D - E, D + 2 * E, 0, 0)
    return a.cut(b)


def v_groove():                            # 90 degree V along X, apex R*sqrt(2) under the tube centre
    pts = [(-V_HW - E, BT + E), (V_HW + E, BT + E), (0.0, BT - V_HW)]
    pts = [(YC + y, z) for y, z in pts]
    xw = XO + E
    return cq.Workplane("YZ").polyline(pts).close().extrude(2 * xw).translate((-xw, 0, 0))


def clamp_block():
    w = 2 * XO - 2 * CORNER
    return prism(w, BT - ZT + CORNER, 0, D, 0, (BT + ZT - CORNER) / 2)


def build_housing():
    h = outline(0, D).union(clamp_block())
    h = h.cut(prism(CX, CZ, FW, D + E, 0, 0))                                 # cavity
    h = h.cut(prism(WIN + FIT, WIN + FIT, -E, WIN_RECESS, LENS_XH, LENS_Z))    # window seat, open to the outside
    h = h.cut(ycyl(NOSE_D / 2 + FIT, WIN_RECESS - E, FW + E, LENS_XH, LENS_Z))  # bore for the lens barrel
    for x, z in HOLES:                                                        # PCB posts with locating pins
        h = h.union(ycyl(POST_R, FW - E, PCB_Y0, x, z)).union(ycyl(HOLE_D / 2 - 0.2, PCB_Y0, PCB_Y1, x, z))
    h = h.cut(groove_ring())
    for sx in (-1, 1):
        h = h.union(rail(sx))
    h = h.cut(v_groove())
    for x, y in SCREWS:                                                       # blind clamp inserts
        h = h.cut(zcyl(INS_D / 2, BT - INS_DEEP, BT + E, x, y))
    return h.cut(ribbon_slot())


def build_lid():
    lid = outline(D, D + LID_T)
    for sx in (-1, 1):                     # flanges beside the rails, held by the lock bars
        x0, x1 = side_x(sx, XO - E, XO + FL)
        lid = lid.union(prism(x1 - x0, 2 * ZF, D, D + LID_T, (x0 + x1) / 2, 0))
    lip = prism(CX - 2 * FIT, CZ - 2 * FIT, D - LIP_H, D + E, 0, 0)
    lid = lid.union(lip.cut(prism(CX - 2 * FIT - 2 * LIP_T, CZ - 2 * FIT - 2 * LIP_T, D - LIP_H - E, D + 2 * E, 0, 0)))
    for x, z in HOLES:
        lid = lid.union(ycyl(PEG_D / 2, PCB_Y1 + PEG_GAP, D + E, x, z))
    return lid


def ribbon_slot():                         # straight down through the floor, under the connector
    return prism(SLOT_W, RIM + 2 * E, RIB_Y - SLOT_T / 2, RIB_Y + SLOT_T / 2, 0, (ZB - CZ / 2) / 2)


def build_cap():
    cap = prism(CAP_L, CAP_ZT - CAP_Z0, YC - CAP_W / 2, YC + CAP_W / 2, 0, (CAP_Z0 + CAP_ZT) / 2)
    cap = cap.cut(xcyl(R, -CAP_L, CAP_L, YC, ZC))
    for x, y in SCREWS:
        cap = cap.cut(zcyl(CLR_D / 2, CAP_Z0 - E, CAP_ZT + E, x, y))
        cap = cap.cut(zcyl(HEAD_D / 2, CAP_Z0 + UNDER_HEAD, CAP_ZT + E, x, y))
    return cap


# ----------------------------------------------------------------------------- fit-check dummies
def camera_dummy():
    pcb = prism(CAM_W, CAM_H, PCB_Y0, PCB_Y1, 0, BZ0 + CAM_H / 2)
    for x, z in HOLES:
        pcb = pcb.cut(ycyl(HOLE_D / 2, PCB_Y0 - E, PCB_Y1 + E, x, z))
    lens = prism(LENS_W, LENS_W, PCB_Y0 - LENS_H, PCB_Y0, LENS_XH, LENS_Z)
    lens = lens.union(ycyl(NOSE_D / 2, PCB_Y0 - LENS_TOP, PCB_Y0 - LENS_H + 0.01, LENS_XH, LENS_Z))
    conn = prism(CONN_W, CONN_H, PCB_Y1, PCB_Y1 + BACK_H, 0, BZ0 + CONN_H / 2)
    return pcb.union(lens).union(conn)


def ribbon_dummy():                        # the flat ribbon, straight down from the connector to 10 mm under the housing
    return prism(RIB_W, BZ0 - ZB + 10, RIB_Y - 0.15, RIB_Y + 0.15, 0, (BZ0 + ZB - 10) / 2)


def window_dummy():
    return prism(WIN, WIN, WIN_RECESS - WIN_T, WIN_RECESS, LENS_XH, LENS_Z)


def tube_dummy():
    return xcyl(RACK_D / 2, -XO - 30, XO + 30, YC, ZC)


def checks(housing, lid, cap):
    cam, win, tube, rib = camera_dummy(), window_dummy(), tube_dummy(), ribbon_dummy()
    for name, s in (("housing", housing), ("lid", lid), ("cap", cap)):
        b = s.val().BoundingBox()
        print(f"{name:<8} vol {vol(s):7.0f} mm3  solids {s.solids().size()}  valid {s.val().isValid()}  "
              f"{b.xlen:.1f} x {b.ylen:.1f} x {b.zlen:.1f}")
        assert s.solids().size() == 1, f"{name} is not one solid"
        assert s.val().isValid(), f"{name} is not valid"
    for dn, d in (("camera board", cam), ("window plate", win), ("rack tube", tube), ("ribbon", rib)):
        for pn, p in (("housing", housing), ("lid", lid), ("cap", cap)):
            assert vol(p.intersect(d)) < 0.01, f"{pn} clashes with {dn}"
    assert vol(housing.intersect(lid)) < 0.01, "lid overlaps housing"
    assert vol(housing.intersect(cap)) < 0.01, "cap overlaps housing"
    assert 2 * POST_R <= PAD_D, "posts wider than the board's pads"
    assert TUBE_UP < R / math.sqrt(2), "tube sits too high to touch both sides of the V"
    assert BT - INS_DEEP >= CZ / 2 + 0.99 and BT - V_HW >= CZ / 2 + 1.99, "clamp inserts or V too close to the cavity"
    # field of view: the cone from the glass must pass the barrel bore and the window plate
    t = math.tan(math.radians(FOV_D / 2))
    assert GLASS_D / 2 + LG * t <= NOSE_D / 2 + FIT, "the bore in the front wall cuts the picture"
    assert GLASS_D / 2 + (LG + WIN_T) * t <= WIN / 2 - 1.0, "the window plate is too small for the field of view"
    # the gasket groove must not run into an insert or the ribbon slot
    ring = groove_ring()
    for x, y in SCREWS:
        assert vol(ring.intersect(zcyl(INS_D / 2 + 1.0, BT - INS_DEEP, BT + E, x, y))) < 0.01, "groove too close to a clamp insert"
    assert SLOT_W <= CX and SLOT_W >= RIB_W + 2 * FIT, "ribbon slot wider than the cavity or narrower than the ribbon"
    assert RIB_Y + SLOT_T / 2 <= D - GROOVE_D - 2.0, "ribbon slot too close to the gasket groove"
    assert vol(housing.intersect(prism(CONN_W, CONN_H, PCB_Y1, PCB_Y1 + BACK_H, 0, BZ0 + CONN_H / 2))) < 0.01, "connector hits the housing"
    # lock bars: each slides down from above without touching anything, sits on the rail and flange tops when home,
    # and holds the lid against the cord; the taper must be shallow enough to stay put (self-locking)
    for sx in (-1, 1):
        bar = build_bar(sx)
        assert bar.solids().size() == 1 and bar.val().isValid(), "lock bar is not one valid solid"
        for part, name in ((housing, "housing"), (lid, "lid"), (cap, "cap"), (tube, "rack tube"), (cam, "camera")):
            for i in range(9):
                assert vol(part.intersect(bar.translate((0, 0, (2 * ZF + HEAD + 2) * i / 8)))) < 0.01, f"lock bar hits the {name}"
        assert vol(housing.intersect(bar.translate((0, 0, -0.3)))) > 0.01, "lock bar does not sit on the rail"
        assert vol(bar.intersect(lid.translate((0, SL_PLAY + 0.2, 0)))) > 0.01, "lock bar does not hold the lid"
    slope = TAPER / (2 * ZF)
    assert slope <= 0.05, f"rail taper {slope:.3f} too steep to stay locked"
    assert TAPER + SL_PLAY < CORD - GROOVE_D, "the taper must pull in less than the cord squeeze"
    screw = UNDER_HEAD + CAP_GAP + INS_DEEP - 1.0
    print(f"lock bars {2 * ZF + HEAD:.1f} mm long, wall {BAR_T}; rail taper {TAPER} mm (slope {slope:.3f})")
    print(f"housing {2 * XB1:.1f} x {D:.1f} x {BT - ZB:.1f} mm (+ lid {LID_T}, cap to {CAP_ZT - ZB:.1f} mm high); "
          f"front wall {FW:.2f}; board front at y {PCB_Y0:.2f}; behind the connector {D - PCB_Y1 - BACK_H:.1f} mm")
    print(f"rack tube d {RACK_D} + pad {RACK_PAD}: centre {ZC - ZT:.1f} mm above the body, y {YC:.1f}; screws {2 * SD:.1f} mm apart, "
          f"M3 x {math.floor(screw / 2) * 2:.0f} or shorter; cord {100 * (CORD - GROOVE_D) / CORD:.0f} % squeeze")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "out"))
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    import trimesh
    from plate3mf import export_3mf
    os.makedirs(a.out, exist_ok=True)
    housing, lid, cap, bar = build_housing(), build_lid(), build_cap(), build_bar()
    checks(housing, lid, cap)
    tag = "_" + a.tag if a.tag else ""
    f = lambda n, ext: os.path.join(a.out, n + tag + ext)
    # print orientation: housing front face down; lid outer face down (pegs up); cap top down (groove up);
    # lock bar on its back (the outer face), open side up
    hp = housing.rotate((0, 0, 0), (1, 0, 0), 90)
    lp = lid.rotate((0, 0, 0), (1, 0, 0), -90)
    cp = cap.rotate((0, 0, 0), (1, 0, 0), 180)
    bp = bar.rotate((0, 0, 0), (0, 1, 0), 90)
    for n, s in (("camera_housing", hp), ("camera_lid", lp), ("camera_cap", cp), ("camera_lock", bp)):
        z0 = s.val().BoundingBox().zmin
        s = s.translate((0, 0, -z0))
        cq.exporters.export(s, f(n, ".step"))
        cq.exporters.export(s, f(n, ".stl"), tolerance=0.02)

    def put(m, x, y):
        m = m.copy()
        c = m.bounds.mean(axis=0)
        m.apply_translation([x - c[0], y - c[1], -m.bounds[0][2]])
        return m
    parts = {"camera_housing": put(trimesh.load(f("camera_housing", ".stl")), -32, 0),
             "camera_lid": put(trimesh.load(f("camera_lid", ".stl")), 32, 0),
             "camera_cap": put(trimesh.load(f("camera_cap", ".stl")), 0, 45)}
    lock = trimesh.load(f("camera_lock", ".stl"))
    mirrored = lock.copy()
    mirrored.apply_transform(trimesh.transformations.reflection_matrix([0, 0, 0], [0, 1, 0]))   # the other side
    parts["camera_lock_right"] = put(lock, -20, -45)
    parts["camera_lock_left"] = put(mirrored, 20, -45)
    export_3mf(parts, f("camera_plate", ".3mf"))
    trimesh.util.concatenate(list(parts.values())).export(f("camera_plate", ".stl"))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
