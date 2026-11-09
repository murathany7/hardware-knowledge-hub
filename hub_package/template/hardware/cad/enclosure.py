"""Parametric tray for the bike logger's IP65 box (200 x 120 x 75 mm, inner clear 112.5 x 173.5 x 60).

Run:  python hardware/cad/enclosure.py [--out hardware/cad/out]
Edit the PARAMETERS block, run again, print the plate. Everything is derived from it.

Layout (tray frame, X right, Y up the long side, origin = centre of the tray, Z up from the box floor):
  - Pi 5 in its case, standing "vertical" (61 across X, 90 along Y) against the -X rim, USB end towards +Y.
  - Breadboard (87 x 54) stands on its edge against the +X big wall, glued to the box wall; holder = ledge + 2 end walls.
  - IMU (BNO085, 25.6 x 22.7) in a pocket on the floor at the -Y end, hinged snap lid, cable openings along Y.
  - GPS receiver (50 x 38 x 20) in a pocket in the cable zone at the +Y end, cable leaves towards the Pi.
  - Cable trunk: a covered channel (open at both Y ends) on a floor spine between the IMU pocket and the Pi pocket;
    the lid is a separate part that snaps on from above.
"""
import argparse
import json
import os
import pathlib

import cadquery as cq

# ----------------------------------------------------------------------------- PARAMETERS (mm)
# The numbers live in parameters.json (labelled, editable in the editor: python3 hardware/knowledge/kb.py serve).
P = {p["key"]: p["value"] for p in json.loads(pathlib.Path(__file__).with_name("parameters.json").read_text())["parameters"]}
W, L = P["W"], P["L"]                                        # clear space inside the box (tray outline)
FT, RX, RY, WR, OR = P["FT"], P["RX"], P["RY"], P["WR"], P["OR"]   # floor thickness, rim widths, window radius, outer radius
LIP_W, LIP_H = P["LIP_W"], P["LIP_H"]                          # raised edge lip: width, height above the frame
FIT, WALL, E = P["FIT"], P["WALL"], 1.0                      # clearance per side, pocket wall, boolean overshoot
PI, IMU = (P["PI_X"], P["PI_Y"]), (P["IMU_X"], P["IMU_Y"])   # Pi 5 + case footprint (X, Y); BNO085 board (long, short)
PI_H, WALL_H_PI, WALL_H_IMU = P["PI_H"], P["WALL_H_PI"], P["WALL_H_IMU"]
PI_LIFT = P["PI_LIFT"]                                       # Pi pocket sits on a pedestal this high, so its ports clear the neighbouring walls
CZ = P["CZ"]                                                 # cable zone: Pi USB end -> tray +Y end (used when PI_CORNER = 0)
PI_CORNER = bool(P["PI_CORNER"])                              # 1: Pi pocket pushed into the -X/-Y corner
US_TRAY, US_T_WALL, US_T_H = bool(P["US_TRAY"]), P["US_T_WALL"], P["US_T_H"]   # ultrasonic shell pocket: on/off, wall, wall height
PI_INSET, PI_SIDE_INSET, OVERLAP = P["PI_INSET"], P["PI_SIDE_INSET"], P["OVERLAP"]
OPENW = P["OPENW"]                                           # IMU cable opening width
# breadboard standing on edge against the +X wall
BBL, BBT, BBH = P["BBL"], P["BBT"], P["BBH"]                 # length (along Y), thickness (X), height (Z)
BB_GAP = P["BB_GAP"]                                         # breadboard holder starts this far above the IMU pocket
EWT, EWD, EWH = P["EWT"], P["EWD"], P["EWH"]                 # end wall thickness, depth, height
# IMU module position (floor level) and lid
IMX = P["IMX"]                                               # IMU centre X; its -Y edge is set per variant in set_layout
LID_T, LID_CLR = P["LID_T"], P["LID_CLR"]
EAR_R, EAR_W, EAR_X, PIN_HOLE, BARREL_HW = P["EAR_R"], P["EAR_W"], P["EAR_X"], P["PIN_HOLE"], P["BARREL_HW"]
ARM_T, ARM_HW, BUMP, BARB = P["ARM_T"], P["ARM_HW"], P["BUMP"], P["BARB"]
# GPS receiver pocket
GPS = (P["GPS_X"], P["GPS_Y"], P["GPS_H"])                   # long X, short Y, height (cable leaves the -X short end, centre)
GWALL_H, GCABLE_W = P["GWALL_H"], P["GCABLE_W"]
NOTCH = (P["NOTCH_X"], P["NOTCH_Y"])                         # box corner post cut-out of the notched tray (X, Y)
# cable trunk
CH_ON = bool(P["CH_ON"])                                   # 0 leaves the cable channel and its lid out
TX = P["TX"]                                                 # channel centre across the tray
CH_W, CH_H, CH_WALL, CH_FLOOR = P["CH_W"], P["CH_H"], P["CH_WALL"], P["CH_FLOOR"]   # channel inner width, wall height, wall, floor
CH_LID_T, CH_LID_OVER, CH_TAB_H = P["CH_LID_T"], P["CH_LID_OVER"], P["CH_TAB_H"]    # lid plate, pull tab overhang, snap tab height
CH_OUT = CH_W + 2 * CH_WALL                                  # channel outer width
TAB_LEN, TAB_T, DIMPLE_R, BUMP_R, TAB_CLR = 10.0, 1.0, 0.75, 0.55, 0.15   # snap tab length/thickness, wall dimple, tab bump, tab clearance
# ----------------------------------------------------------------------------- derived
o = lambda c: (c[0] + 2 * (FIT + WALL), c[1] + 2 * (FIT + WALL))     # pocket outer from inner part size
i = lambda c: (c[0] + 2 * FIT, c[1] + 2 * FIT)
top = L / 2 - CZ
pcy = top - o(PI)[1] / 2
pcx = -(W / 2 - RX + OVERLAP) + o(PI)[0] / 2
OX, OY = o(IMU)
go = o(GPS[:2])


def blk(x, y, z, cx, cy, z0):
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, False)).translate((cx, cy, z0))


def cyl(r, h, cx, cy, z0):
    return cq.Workplane("XY").circle(r).extrude(h).translate((cx, cy, z0))


def xcyl(r, xa, xb, y, z):
    return cq.Workplane("YZ").circle(r).extrude(xb - xa).translate((xa, y, z))


def ycyl(r, ya, yb, x, z):
    return cq.Workplane("XZ").circle(r).extrude(ya - yb).translate((x, ya, z))


def wedge(pts, xa, xb):
    return cq.Workplane("YZ").polyline(pts).close().extrude(xb - xa).translate((xa, 0, 0))


def rrect(w, l, r, h, z0):
    s = blk(w - 2 * r, l, h, 0, 0, z0).union(blk(w, l - 2 * r, h, 0, 0, z0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            s = s.union(cyl(r, h, sx * (w / 2 - r), sy * (l / 2 - r), z0))
    return s


def vol(s):
    return s.val().Volume() if s.vals() else 0.0


# ----------------------------------------------------------------------------- IMU module (local frame: plugs +-X, hinge -Y, latch +Y)
WT = FT + WALL_H_IMU                      # top of the pocket wall
YM, Y0 = -OY / 2, OY / 2
YAX = YM + (FIT + WALL) / 2               # hinge axis over the wall centre
ZAX = WT + LID_CLR + LID_T / 2
BR = LID_T / 2


def imu_module():
    ring = blk(OX, OY, WALL_H_IMU, 0, 0, FT).cut(blk(*i(IMU), WALL_H_IMU + 2 * E, 0, 0, FT - E))
    for sx in (-1, 1):
        ring = ring.cut(blk(3 * WALL, OPENW, WALL_H_IMU + 2 * E, sx * (OX / 2 - WALL / 2), 0, FT))
    for sx in (-1, 1):                    # hinge ears + pin hole
        xc = sx * EAR_X
        ring = ring.union(blk(EAR_W, 2 * EAR_R, ZAX - WT, xc, YAX, WT).union(xcyl(EAR_R, xc - EAR_W / 2, xc + EAR_W / 2, YAX, ZAX)))
    for sx in (-1, 1):
        ring = ring.cut(xcyl(PIN_HOLE / 2, sx * EAR_X - EAR_W / 2 - 1, sx * EAR_X + EAR_W / 2 + 1, YAX, ZAX))
    ring = ring.union(wedge([(Y0 - 0.2, WT - 4.0), (Y0 + BUMP, WT - 3.0), (Y0 - 0.2, WT - 2.0)], -ARM_HW, ARM_HW))   # snap catch
    return ring.union(blk(OX, OY, FT, 0, 0, 0))                                                          # floor plate


def imu_lid():
    z0 = WT + LID_CLR
    z1 = z0 + LID_T
    plate = blk(OX - 0.6, Y0 - YAX, LID_T, 0, (YAX + Y0) / 2, z0)
    for sx in (-1, 1):
        plate = plate.cut(blk(EAR_W + 0.5, EAR_R + 1.5, LID_T + 2, sx * EAR_X, (YAX - 1.0 + YAX + EAR_R + 0.5) / 2, z0 - 1))
    lid = plate.union(xcyl(BR, -BARREL_HW, BARREL_HW, YAX, ZAX)).cut(xcyl(PIN_HOLE / 2, -BARREL_HW - 1, BARREL_HW + 1, YAX, ZAX))
    yi = Y0 + 1.2
    lid = lid.union(blk(2 * ARM_HW, 2.6, LID_T, 0, Y0 + 1.1, z0))                                  # bridge
    lid = lid.union(blk(2 * ARM_HW, 4.6, 2.0, 0, Y0 + 2.4 + 2.3, z1 - 2.0))                       # thumb tab
    lid = lid.union(blk(2 * ARM_HW, ARM_T, z1 - (WT - 5.2), 0, yi + ARM_T / 2, WT - 5.2))          # flexible arm
    k = 1.0 / BUMP
    return lid.union(wedge([(yi + 0.01, WT - 4.2 + k * 1.2), (yi - BARB, WT - 4.2 + k * (1.2 - BARB)), (yi + 0.01, WT - 4.9)], -ARM_HW, ARM_HW))


def place_imu(m):                          # latch faces +X (the box wall), hinge faces the Pi, plugs end up on +-Y
    return m.rotate((0, 0, 0), (0, 0, 1), -90).translate((IMX, IMY, 0))


# ----------------------------------------------------------------------------- breadboard holder, GPS pocket, cable trunk
hlen = BBL + 2 * FIT + 2 * EWT
xb = W / 2 - 0.4                           # back of the breadboard (the box wall)
xf = xb - (BBT + 2 * FIT)                  # front of the breadboard seat


def set_layout(notches):
    """Stack along Y: IMU pocket at the -Y end, breadboard holder above it, GPS pocket in the +Y corner.
    The notched tray has box corner posts, so the IMU stays clear of them and the GPS sits beside the +X post."""
    global IMY, hy0, hy1, hcy, GCX, gcy, imu_top, top, pcy
    if PI_CORNER:                          # Pi pocket against the -Y end (on the notched tray, just above the post cut-out)
        top = -L / 2 + (NOTCH[1] + 0.5 if notches else 0.0) + o(PI)[1]
        pcy = top - o(PI)[1] / 2
    imy_edge = -74.5 if notches else -(L / 2) + 0.4
    IMY = imy_edge + OX / 2
    imu_top = imy_edge + OX
    hy0 = imu_top + BB_GAP
    hy1 = hy0 + hlen
    hcy = (hy0 + hy1) / 2
    GCX = (W / 2 - NOTCH[0] - 0.5 if notches else xb) - go[0] / 2
    gcy = L / 2 - 0.4 - go[1] / 2


def holder():
    h = blk(EWD, EWT, EWH, xb - EWD / 2 + 0.4, hy0 + EWT / 2, 0).union(blk(EWD, EWT, EWH, xb - EWD / 2 + 0.4, hy1 - EWT / 2, 0))
    return h.union(blk(xb - (xf - 1.0) + 0.4, hlen, FT, (xb + xf - 1.0) / 2, hcy, 0))


def gps_walls():
    pk = blk(*go, GWALL_H + FT, GCX, gcy, 0).cut(blk(*i(GPS[:2]), GWALL_H + FT, GCX, gcy, FT))
    return pk.cut(blk(3 * WALL, GCABLE_W, GWALL_H + 2 * E, GCX - go[0] / 2 + WALL / 2, gcy, FT))


def gps_pocket(t):
    t = t.union(gps_walls())
    for dx in (-12, 12):                   # tie slots under the receiver
        t = t.cut(blk(9, 2.6, FT + 2 * E, GCX + dx, gcy + i(GPS[:2])[1] / 2 - 2.5, -E))
        t = t.cut(blk(9, 2.6, FT + 2 * E, GCX + dx, gcy - i(GPS[:2])[1] / 2 + 2.5, -E))
    return t


def shell_geom():
    """Ultrasonic shell (box + lid) upside down: lid on the tray floor, probe cable hole facing the box lid. Returns the pocket
    centre, the closed shell's size and a dummy of the shell for the fit checks. Uses the corner next to the +Y end, -X side."""
    import ultrasonic_box as us
    sw, sd, sh = 2 * us.XO, 2 * us.YO, us.H + us.LID_T
    cx = -(W / 2 - LIP_W) + US_T_WALL + FIT + sw / 2
    cy = (L / 2 - LIP_W) - US_T_WALL - FIT - sd / 2
    dummy = us.outline(0, sh).translate((-us.CXM, -us.CYM, 0)).rotate((0, 0, 0), (1, 0, 0), 180).translate((cx, cy, FT + sh))   # flipped about X: the wire notch stays on +X
    return cx, cy, sw, sd, sh, us, dummy


def shell_pocket():
    """Plate and walls round the upside-down ultrasonic shell, with a slot in the +X wall for the soldered wires."""
    cx, cy, sw, sd, _sh, us, _ = shell_geom()
    ow, od = sw + 2 * (FIT + US_T_WALL), sd + 2 * (FIT + US_T_WALL)
    ring = blk(ow, od, US_T_H, cx, cy, FT).cut(blk(sw + 2 * FIT, sd + 2 * FIT, US_T_H + 2 * E, cx, cy, FT - E))
    ring = ring.cut(blk(3 * US_T_WALL, us.WIRE_D + 4.0, US_T_H + 2 * E, cx + ow / 2 - US_T_WALL / 2, cy, FT))
    return blk(ow, od, FT, cx, cy, 0).union(ring)


def trunk_span():
    ya, yb = imu_top + 2.0, 39.5            # walls start 2 mm past the IMU pocket so its lid and latch stay free
    return ya, yb, (ya + yb) / 2


def trunk_solid():
    """Floor spine with a cable channel along Y, open at both ends. Cables come in at one end and leave at the other;
    the lid (cable_lid) rests on the walls and snaps into a dimple on each inner wall face."""
    ya, yb, cy = trunk_span()
    ln = yb - ya
    spine = blk(CH_OUT + 2, ln + 4, FT, TX, cy - 2, 0)
    ch = blk(CH_OUT, ln, CH_FLOOR + CH_H, TX, cy, FT).cut(blk(CH_W, ln + 2, CH_H + E, TX, cy, FT + CH_FLOOR))
    for sx in (-1, 1):
        for sy in (-1, 1):
            ch = ch.cut(ycyl(DIMPLE_R, cy + sy * ln / 4 - (TAB_LEN + 2) / 2, cy + sy * ln / 4 + (TAB_LEN + 2) / 2,
                             TX + sx * CH_W / 2, FT + CH_FLOOR + CH_H - CH_TAB_H + 1.5))
    return spine.union(ch)


def trunk(t):
    return t.union(trunk_solid())


def cable_lid():
    """Lid in tray position (plate on top of the walls, snap tabs hanging down into the channel)."""
    ya, yb, cy = trunk_span()
    ln = yb - ya
    zt = FT + CH_FLOOR + CH_H
    lid = blk(CH_OUT, ln + CH_LID_OVER, CH_LID_T, TX, cy - CH_LID_OVER / 2, zt)
    xo = CH_W / 2 - TAB_CLR
    for sx in (-1, 1):
        for sy in (-1, 1):
            y = cy + sy * ln / 4
            lid = lid.union(blk(TAB_T, TAB_LEN, CH_TAB_H, TX + sx * (xo - TAB_T / 2), y, zt - CH_TAB_H))
            lid = lid.union(ycyl(BUMP_R, y - TAB_LEN / 2, y + TAB_LEN / 2, TX + sx * xo, zt - CH_TAB_H + 1.5))
    return lid


def pi_pocket():
    """Pedestal plus the walls round the Pi case (open at the USB end and on the USB-C / HDMI side)."""
    zp = FT + PI_LIFT
    ring = blk(*o(PI), WALL_H_PI, pcx, pcy, zp).cut(blk(*i(PI), WALL_H_PI + 2 * E, pcx, pcy, zp - E))
    ring = ring.cut(blk(i(PI)[0] - 2 * PI_INSET, 3 * WALL, WALL_H_PI + 2 * E, pcx, pcy + o(PI)[1] / 2 - WALL / 2, zp))   # +Y end open (USB/Ethernet)
    ring = ring.cut(blk(3 * WALL, i(PI)[1] - 2 * PI_SIDE_INSET, WALL_H_PI + 2 * E, pcx + o(PI)[0] / 2 - WALL / 2, pcy, zp))  # +X side open (USB-C/HDMI)
    return blk(*o(PI), zp, pcx, pcy, 0).union(ring)


def frame(notches):
    """The 3 mm frame with its raised edge lip: rim, strap slots and (notched tray) the corner cut-outs."""
    t = rrect(W, L, OR, FT, 0).cut(rrect(W - 2 * RX, L - 2 * RY, WR, FT + 2 * E, -E))
    if LIP_W > 0 and LIP_H > 0:            # raised edge lip: same footprint, much stiffer in bending
        lip = rrect(W, L, OR, FT + LIP_H, 0).cut(rrect(W - 2 * LIP_W, L - 2 * LIP_W, max(OR - LIP_W, 0.5), FT + LIP_H + 2 * E, -E))
        t = t.union(lip.cut(blk(LIP_W + 2 * E, hlen, FT + LIP_H + 2 * E, W / 2 - LIP_W / 2, hcy, -E)))   # none where the breadboard is glued to the wall
    if notches:                            # keep the rim strips attached when the corners are cut away
        for ya, yb in ((top - 1.0, L / 2 - RY / 2), (-(L / 2 - RY / 2), pcy - o(PI)[1] / 2 + 1.0)):
            t = t.union(blk(6.0, yb - ya, FT, -31.0, (ya + yb) / 2, 0))
        ya = pcy - o(PI)[1] / 2 - 5.0 - 3.0
        yb = max(ya + 6.0, IMY - OX / 2 + 1.0) if PI_CORNER else ya + 6.0      # in the corner the strip must reach the IMU pocket
        t = t.union(blk(W - 2 * RX + 2 * OVERLAP, yb - ya, FT, 0, (ya + yb) / 2, 0))
    cut = None
    for sy in (-1, 1):                     # strap slots in the -X rim
        b = blk(2.6, 9, FT + 2 * E, -(W / 2 - RX / 2), pcy + sy * 18, -E)
        cut = b if cut is None else cut.union(b)
    if notches:
        for sx in (-1, 1):
            for sy in (-1, 1):
                cut = cut.union(blk(*NOTCH, 80, sx * (W / 2 - NOTCH[0] / 2), sy * (L / 2 - NOTCH[1] / 2), -E))
    return t.cut(cut)


def build_tray(notches):
    set_layout(notches)
    t = frame(notches).union(pi_pocket())
    t = gps_pocket(t.union(holder()).union(place_imu(imu_module())))
    if US_TRAY and not notches:            # the notched tray has no room for it
        t = t.union(shell_pocket())
    return trunk(t) if CH_ON else t


# ----------------------------------------------------------------------------- fit-check dummies
def bno085_dummy():                        # 25.6 x 22.7 x 4.6, JST-SH plugs on the +-Y edges (plug width estimated)
    pcb = cq.Workplane("XY").box(22.7, 24.0, 1.6, centered=(True, True, False))
    pcb = pcb.faces(">Z").workplane().pushPoints([(sx * 9.5, sy * 10.5) for sx in (-1, 1) for sy in (-1, 1)]).hole(2.5)
    for sy in (-1, 1):
        pcb = pcb.union(cq.Workplane("XY").box(7.2, 3.4, 3.0, centered=(True, True, False)).translate((0, sy * (12.0 + 0.8 - 1.7), 1.6)))
    return pcb.union(cq.Workplane("XY").box(6, 6, 1, centered=(True, True, False)).translate((2, -1, 1.6)))


def checks(tray, tray_n, lid):
    wall = blk(10, L + 20, 80, W / 2 + 5, 0, -5)
    for name, t, n in (("tray", tray, False), ("tray_notched", tray_n, True)):
        set_layout(n)
        pi_case = blk(*PI, PI_H, pcx, pcy, FT + PI_LIFT)
        gps = blk(*GPS, GCX, gcy, FT)
        bb = blk(BBT, BBL, BBH, xb - BBT / 2, hcy, FT)
        imu = place_imu(bno085_dummy().rotate((0, 0, 0), (0, 0, 1), 90).translate((0, 0, FT)))
        b = t.val().BoundingBox()
        print(f"{name:<13} vol {vol(t):7.0f} mm3  solids {t.solids().size()}  valid {t.val().isValid()}  "
              f"{b.xlen:.1f} x {b.ylen:.1f} x {b.zlen:.1f}")
        assert t.solids().size() == 1, f"{name} is not one solid"
        for dn, d in (("Pi case", pi_case), ("GPS", gps), ("breadboard", bb), ("IMU board", imu), ("box wall", wall)):
            assert vol(t.intersect(d)) < 0.01, f"{name} clashes with {dn}"
        assert gcy + go[1] / 2 <= L / 2 and GCX + go[0] / 2 <= W / 2, f"{name}: GPS pocket outside the tray"
        if US_TRAY and not n:
            cx, cy, _sw, sd, sh, us, shell = shell_geom()
            assert vol(t.intersect(shell)) < 0.01, f"{name}: ultrasonic shell clashes with the tray"
            assert vol(shell.intersect(pi_case)) < 0.01 and vol(shell.intersect(gps)) < 0.01 and vol(shell.intersect(wall)) < 0.01, f"{name}: ultrasonic shell clashes with the Pi, GPS or box wall"
            assert vol(shell_pocket().intersect(pi_case)) < 0.01 and vol(shell_pocket().intersect(gps)) < 0.01, f"{name}: shell pocket clashes with the Pi or GPS"
            assert FT + sh <= 57.0, "ultrasonic shell is within 3 mm of the box lid"
            print(f"  ultrasonic shell: upside down, cable hole at x {cx + (us.XH - us.CXM):.1f}, y {cy + (us.CYM - us.YH):.1f}, top {FT + sh:.1f} mm; "
                  f"{(cy - sd / 2 - FIT - US_T_WALL) - (pcy + o(PI)[1] / 2):.1f} mm between the Pi's USB end and the pocket")
        assert hy1 < gcy - go[1] / 2 or GCX + go[0] / 2 < xf, f"{name}: breadboard holder meets the GPS pocket"
        print(f"  GPS pocket: {W / 2 - (GCX + go[0] / 2):.1f} mm from the +X wall, {L / 2 - (gcy + go[1] / 2):.1f} mm from the +Y end; "
              f"front space for breadboard wires {xf - (pcx + o(PI)[0] / 2):.1f} mm (Pi pocket)")
        lid_p = place_imu(lid)
        assert vol(lid_p.intersect(t)) < 0.01 and vol(lid_p.intersect(imu)) < 0.01, f"{name}: closed lid clashes"
        for ang in (30, 60, 90):
            r = place_imu(lid.rotate((0, YAX, ZAX), (1, YAX, ZAX), ang))
            assert vol(r.intersect(t)) < 0.01 and vol(r.intersect(pi_case)) < 0.01, f"{name}: lid clashes at {ang} deg"
    if not CH_ON:
        print("cable channel: off")
        print("IMU lid: closed ok, opens to 90 deg without touching the Pi case or tray")
        return
    assert CH_WALL - DIMPLE_R >= 1.6, "cable channel wall too thin at the snap dimples"
    assert TX + CH_OUT / 2 + 2.0 < xf, "cable channel reaches the breadboard"
    assert FT + CH_FLOOR + CH_H + CH_LID_T <= 57.0, "cable lid is within 3 mm of the box lid"
    for name, t, n in (("tray", tray, False), ("tray_notched", tray_n, True)):
        set_layout(n)
        clid = cable_lid()
        assert clid.solids().size() == 1 and clid.val().isValid(), f"{name}: cable lid is not one valid solid"
        assert vol(clid.intersect(t)) < 0.01, f"{name}: cable lid clashes with the tray"
        assert vol(clid.intersect(place_imu(lid))) < 0.01, f"{name}: cable lid clashes with the IMU lid"
    print("cable lid: fits the channel, clear of tray and IMU lid")
    print("IMU lid: closed ok, opens to 90 deg without touching the Pi case or tray")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "out"))
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    import trimesh
    from plate3mf import export_3mf
    os.makedirs(a.out, exist_ok=True)
    tray, tray_n = build_tray(False), build_tray(True)
    lid = imu_lid()
    checks(tray, tray_n, lid)
    tag = "_" + a.tag if a.tag else ""
    f = lambda n, ext: os.path.join(a.out, n + tag + ext)
    for n, s in (("bike_tray", tray), ("bike_tray_notched", tray_n)):
        cq.exporters.export(s, f(n, ".step"))
        cq.exporters.export(s, f(n, ".stl"), tolerance=0.02)
    flat = lid.rotate((0, 0, 0), (1, 0, 0), 180)                    # print flat side down
    cq.exporters.export(flat, f("imu_lid", ".step"))
    cq.exporters.export(flat, f("imu_lid", ".stl"), tolerance=0.02)
    for n, notches in ((("cable_lid", False), ("cable_lid_notched", True)) if CH_ON else ()):    # the channel starts at a different Y per variant
        set_layout(notches)
        cflat = cable_lid().rotate((0, 0, 0), (1, 0, 0), 180)       # plate face down, snap tabs up
        cq.exporters.export(cflat, f(n, ".step"))
        cq.exporters.export(cflat, f(n, ".stl"), tolerance=0.02)

    def put(m, x, y):
        m = m.copy()
        c = m.bounds.mean(axis=0)
        m.apply_translation([x - c[0], y - c[1], 0])
        m.apply_translation([0, 0, -m.bounds[0][2]])
        return m
    ld = trimesh.load(f("imu_lid", ".stl"))
    for tn, cn, pn in (("bike_tray", "cable_lid", "bike_plate1"), ("bike_tray_notched", "cable_lid_notched", "bike_plate2_notched")):
        parts = {"tray": put(trimesh.load(f(tn, ".stl")), -30, 0), "imu_lid": put(ld, 70, 0)}
        if CH_ON:
            parts["cable_lid"] = put(trimesh.load(f(cn, ".stl")), 100, 0)
        export_3mf(parts, f(pn, ".3mf"))
        trimesh.util.concatenate(list(parts.values())).export(f(pn, ".stl"))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
