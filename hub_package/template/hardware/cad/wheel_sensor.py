"""Clip-on bracket that holds one KY-003 / A3144 Hall board next to the spokes, for the wheel speed sensor.
One printed part, no screws: it clamps to the left (non-drive side) rear seatstay a few cm above the dropout and the roller brake, with
two zip-ties and a strip of inner tube as a pad, and reads a magnet on a left-side spoke near the hub. (The drive side is closed by
the chain case, and the panniers and the frame lock cover the upper wheel. This spot is free, and the pannier only touches the stay's
outer side.)

Run:  python hardware/cad/wheel_sensor.py [--out hardware/cad/out] [--tag v1] [--count N]
Writes the bracket (wheel_sensor.*, plate wheel_sensor_plate.*) and the clamp alone as a quick fit test on the real stay
(wheel_sensor_fit.*: the same clamp, from the same numbers, without the arm and the sensor holder).
The numbers live in parameters.json (group "Wheel sensor"), editable in the editor: python3 hardware/knowledge/kb.py serve.

Frame: Z along the tube (on the bike: up the seatstay), X from the tube's middle sideways towards the wheel,
Y across the tube (on the bike: front to back). The tube's middle line is the Z axis. The tube section is a D (the Vento's stay
is flat towards the wheel and rounded outside): a flat face on the wheel side (+X) with corner radius R, and a half-ellipse behind it
that runs from the end of those corners round to the outer side (-X). W is the size sideways (flat face to the back of the round),
H front to back. R = H/2 and W = H give a round tube.
The clamp is a C that wraps the wheel side of the tube and follows its shape: the tube snaps in sideways from -X past the clamp's
lips (the D is widest a little inside the mouth). Two zip-ties run
round the tube and through grooves cut into the outside of the clamp. An arm carries the holder to the spoke: its window faces +X,
the Hall board lies behind the window with the chip against it. The pocket is open at the top (+Z) to put the board in, and has
a rectangular cable slot in the middle of its floor for the wires that leave the board's header at that end; fill both with silicone
after soldering. The magnet passes the window at WS_CHIP_GAP from the chip.
Print as modelled (flat bottom down, tube axis vertical). Printed ASA is not guaranteed watertight: the silicone does that.
"""
import argparse
import json
import os
import pathlib

import cadquery as cq

# ----------------------------------------------------------------------------- PARAMETERS (mm)
P = {p["key"]: p["value"] for p in json.loads(pathlib.Path(__file__).with_name("parameters.json").read_text())["parameters"]}
TUBE_W, TUBE_H, TUBE_R = P["WS_TUBE_W"], P["WS_TUBE_H"], P["WS_TUBE_R"]   # seatstay D section (ESTIMATES): flat face corner radius R
PAD = P["WS_PAD"]                                         # the rubber pad round the tube
SPOKE_GAP, CHIP_GAP = P["WS_SPOKE_GAP"], P["WS_CHIP_GAP"] # tube's inner face to the magnet's near face (ESTIMATE), chip to magnet
BOARD_Y, BOARD_Z = P["WS_BOARD_Y"], P["WS_BOARD_Z"]       # KY-003 outline (ESTIMATES)
BOARD_T, COMP_H = P["WS_BOARD_T"], P["WS_COMP_H"]         # PCB thickness, height of the chip and parts above it (ESTIMATE)
CABLE_W = P["WS_CABLE_W"]                                 # cable slot in the middle of the pocket floor
BODY_H, WALL = P["WS_BODY_H"], P["WS_WALL"]
BACK, SIDE = P["WS_BACK"], P["WS_SIDE"]
TIE_W, TIE_T = P["WS_TIE_W"], P["WS_TIE_T"]               # groove height along the tube and depth
FIT, E = 0.4, 1.0                                         # clearance per side, boolean overshoot
CORNER = 2.0                                              # rounded vertical edges of the clamp
TIE_EDGE = 2.0                                            # solid below the lower groove and above the upper one
GROOVE_CLEAR = 1.0                                        # arm stays this far from the grooves, so they stay open
# ----------------------------------------------------------------------------- derived
SPOKE_X = TUBE_W / 2 + SPOKE_GAP                          # tube middle to the magnet's near face
BW, BH = TUBE_W / 2 + PAD, TUBE_H / 2 + PAD                   # bore half width, half height
BR = TUBE_R + PAD                                         # bore corner radius at the flat face
XB = BW + BACK                                            # back face of the clamp
YB = BH + SIDE                                            # half width of the clamp
RB = min(BR + BACK, XB - CORNER - 0.2, YB - 0.2)          # clamp's back corners: round with the bore where there is room
ZG = (TIE_EDGE + TIE_W / 2, BODY_H - TIE_EDGE - TIE_W / 2)    # groove centres
DEPTH = BOARD_T + COMP_H + FIT                            # pocket depth, window to back wall
XF = SPOKE_X - (CHIP_GAP - WALL)                          # outer face of the window
XR = XF - WALL - DEPTH - WALL                             # back of the holder
HY = BOARD_Y + 2 * FIT + 2 * WALL                         # holder width
ZA0, ZA1 = ZG[0] + TIE_W / 2 + GROOVE_CLEAR, ZG[1] - TIE_W / 2 - GROOVE_CLEAR   # arm height range


def vol(s):
    return s.val().Volume() if s.vals() else 0.0


def blk(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def dsection(hw, hh, r, z0, z1):
    """D-shaped prism round the Z axis, from z0 to z1: flat face at x = +hw with corner radius r, half height hh, and a
    half-ellipse from the corners (x = hw - r) back to x = -hw."""
    xc, a = hw - r, 2 * hw - r
    s = cq.Workplane("XY").ellipse(a, hh).extrude(z1 - z0).translate((xc, 0, z0)).intersect(blk(-hw - E, xc, -hh - E, hh + E, z0, z1))
    s = s.union(blk(xc, hw, -hh + r, hh - r, z0, z1))
    for sy in (-1, 1):
        s = s.union(cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((xc, sy * (hh - r), z0)))
    return s


def snap():
    """How much narrower the clamp's mouth (x = 0) is than the bore at its widest, per side."""
    xc, a = BW - BR, 2 * BW - BR
    return BH - BH * (1 - (xc / a) ** 2) ** 0.5 if xc > 0 else 0.0


def rounded(x0, x1, y0, y1, r_front, r_back, z0, z1):
    """Box with its vertical edges rounded: r_front on the x0 side, r_back on the x1 side."""
    return blk(x0, x1, y0, y1, z0, z1).edges("|Z and <X").fillet(r_front).edges("|Z and >X").fillet(r_back)


def build_clamp():
    """The C that holds the stay, with its zip-tie grooves: printed alone as the fit test, and the base of the bracket."""
    assert 0 < TUBE_R <= TUBE_H / 2 - 0.2, "WS_TUBE_R must be above 0 and at least 0.2 mm under half the stay depth (WS_TUBE_H)"
    assert TUBE_W - TUBE_R >= TUBE_H / 2, "the stay is narrower sideways than this D shape allows: WS_TUBE_W must be at least WS_TUBE_H / 2 + WS_TUBE_R"
    assert snap() <= 1.5, f"the clamp's mouth is {snap():.1f} mm per side narrower than the stay: too tight to snap on"
    body = rounded(0, XB, -YB, YB, CORNER, RB, 0, BODY_H)
    inner = rounded(-E, XB - TIE_T, -(YB - TIE_T), YB - TIE_T, CORNER - TIE_T / 2, RB - TIE_T, -E, BODY_H + E)
    for zc in ZG:                                                                    # grooves round the outside for the zip-ties
        slab = blk(-E, XB + E, -YB - E, YB + E, zc - TIE_W / 2, zc + TIE_W / 2)
        body = body.cut(slab.cut(inner))
    return body.cut(dsection(BW, BH, BR, -E, BODY_H + E))                           # bore: the stay snaps in from -X


def build():
    assert XR >= XB, (f"the magnet is too close to the tube: the holder needs at least {XB + 2 * WALL + DEPTH + CHIP_GAP - WALL - TUBE_W / 2:.1f} mm "
                      f"from the tube's inner face to the magnet (WS_SPOKE_GAP is {SPOKE_GAP:.1f})")
    body = build_clamp()
    arm = blk(XB - E, XR + E, -HY / 2, HY / 2, ZA0, ZA1)
    holder = blk(XR, XF, -HY / 2, HY / 2, 0, BODY_H)
    pocket = blk(XR + WALL, XF - WALL, -(BOARD_Y / 2 + FIT), BOARD_Y / 2 + FIT, WALL, BODY_H + E)     # open at the top
    return body.union(arm).union(holder.cut(pocket).cut(cable_slot()))


def cable_slot():
    """Rectangular hole through the middle of the pocket floor, the full pocket depth, for the board's wires."""
    return blk(XR + WALL, XF - WALL, -CABLE_W / 2, CABLE_W / 2, -E, WALL + E)


# ----------------------------------------------------------------------------- fit-check dummies
def tube_dummy():
    return dsection(TUBE_W / 2, TUBE_H / 2, TUBE_R, -E, BODY_H + E)


def board_dummy():
    """KY-003 in its pocket: component side towards the window, chip against it, the board sitting on the floor."""
    x_comp = XF - WALL                                                               # tops of the parts touch the window
    zb = WALL + FIT
    pcb = blk(x_comp - COMP_H - BOARD_T, x_comp - COMP_H, -BOARD_Y / 2, BOARD_Y / 2, zb, zb + BOARD_Z)
    chip = blk(x_comp - COMP_H, x_comp, -2.25, 2.25, zb + BOARD_Z / 2 - 2.0, zb + BOARD_Z / 2 + 2.0)
    return pcb.union(chip)


def magnet_dummy():
    return blk(SPOKE_X, SPOKE_X + 6.0, -6.0, 6.0, BODY_H / 2 - 6.0, BODY_H / 2 + 6.0)    # a 12 mm magnet; only its near face matters


def checks(part):
    b = part.val().BoundingBox()
    print(f"bracket vol {vol(part):6.0f} mm3  solids {part.solids().size()}  valid {part.val().isValid()}  {b.xlen:.1f} x {b.ylen:.1f} x {b.zlen:.1f}")
    assert part.solids().size() == 1 and part.val().isValid(), "the bracket is not one valid solid"
    assert vol(part.intersect(tube_dummy())) < 0.01, "the bracket clashes with the tube"
    assert vol(part.intersect(board_dummy())) < 0.01, "the bracket clashes with the Hall board"
    assert vol(part.intersect(magnet_dummy())) < 0.01, "the bracket would hit the magnet"
    assert BACK - TIE_T >= WALL and SIDE - TIE_T >= WALL, "the zip-tie groove leaves a wall thinner than WS_WALL"
    assert ZA1 - ZA0 >= 6.0, "the arm between the grooves is under 6 mm high: make the bracket taller"
    assert BOARD_Z + FIT + WALL <= BODY_H, "the Hall board does not fit the bracket height"
    assert 0 < CABLE_W <= BOARD_Y - 4.0, "the cable slot must leave at least 2 mm of floor under each end of the board (WS_CABLE_W)"
    print(f"holder front face {XF:.1f} mm from the tube axis, chip to magnet {CHIP_GAP:.1f} mm ({CHIP_GAP - WALL:.1f} mm air + {WALL:.1f} mm window); "
          f"arm {XR - XB:.1f} mm long; clamp for a {TUBE_W:.0f} x {TUBE_H:.0f} mm D stay (flat-face corners R {TUBE_R:.1f}) with a {PAD:.1f} mm pad, "
          f"mouth {snap():.2f} mm per side narrower than the stay (snap)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "out"))
    ap.add_argument("--tag", default="")
    ap.add_argument("--count", type=int, default=1, help="brackets on the plate")
    a = ap.parse_args()
    import trimesh
    from plate3mf import export_3mf
    os.makedirs(a.out, exist_ok=True)
    part = build()
    checks(part)
    tag = "_" + a.tag if a.tag else ""

    def f(n, ext):
        return os.path.join(a.out, n + tag + ext)
    cq.exporters.export(part, f("wheel_sensor", ".step"))
    cq.exporters.export(part, f("wheel_sensor", ".stl"), tolerance=0.02)
    m = trimesh.load(f("wheel_sensor", ".stl"))
    w, d = m.extents[0] + 4.0, m.extents[1] + 4.0
    cols = max(1, min(a.count, int(246 // w)))
    rows = -(-a.count // cols)
    assert rows * d <= 246, f"{a.count} parts do not fit on the 256 mm plate: print fewer per plate"
    parts = {}
    for n in range(a.count):
        r, c = divmod(n, cols)
        mm = m.copy()
        ctr = mm.bounds.mean(axis=0)
        mm.apply_translation([(c - (cols - 1) / 2) * w - ctr[0], (r - (rows - 1) / 2) * d - ctr[1], -mm.bounds[0][2]])
        parts[f"wheel_sensor_{n + 1}"] = mm
    export_3mf(parts, f("wheel_sensor_plate", ".3mf"))
    trimesh.util.concatenate(list(parts.values())).export(f("wheel_sensor_plate", ".stl"))
    clamp = build_clamp()                                                            # fit test: the clamp alone, on its own plate
    assert vol(clamp.intersect(tube_dummy())) < 0.01, "the clamp clashes with the tube"
    cq.exporters.export(clamp, f("wheel_sensor_fit", ".step"))
    cq.exporters.export(clamp, f("wheel_sensor_fit", ".stl"), tolerance=0.02)
    m = trimesh.load(f("wheel_sensor_fit", ".stl"))
    m.apply_translation([-m.bounds.mean(axis=0)[0], -m.bounds.mean(axis=0)[1], -m.bounds[0][2]])
    export_3mf({"wheel_sensor_fit": m}, f("wheel_sensor_fit", ".3mf"))
    print(f"fit test clamp vol {vol(clamp):6.0f} mm3")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
