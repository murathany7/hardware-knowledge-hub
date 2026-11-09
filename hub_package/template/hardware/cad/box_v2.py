"""Bike logger v2: a printed main box for the rear rack, built around the electronics (all mm).

Run:  .venv-cad/bin/python hardware/cad/box_v2.py [--out hardware/print]

Frame: X along the bike (+X = rear), Y across (+Y = left side), Z up; origin = centre of the box floor's underside.

Two levels inside, so the footprint stays small and every cable has somewhere to go:
  - Floor: the power bank in a low cradle (one cable up to the deck). Charging through a sealed USB-C port in the
    front wall, so the lid stays shut.
  - Deck: a removable 3 mm plate on six columns (M3 inserts), stopping 30 mm short of the rear wall.
    Row A (+Y): Pi 5 in its case, room for its USB plugs, a spare bay with tie slots.
    Row B (-Y): breadboard, GPS (turned so its cable points into the lane). A cable lane between the rows has
    zip-tie anchors, and a slot takes the power cable down to the bank.
  - Rear wall: the four ultrasonic boards stand upright against it, side by side, probe plug facing the wall. Each plug
    sits straight in front of its own gland, so the probe cable runs from the plug out of the box without a bend.
    The boards' bottom edges sit in slots in a ledge on the wall, a screwed clamp bar holds their top edges. Their
    4-pin headers (middle of a long edge) face each other in pairs across a 10 mm wire gap.
  - The IMU sits on the floor beside the bank, fixed to the box itself (best for vibration readings).
  - Gutter: the deck stops 6 mm short of the side and front walls, so cables drop down past it.
  - Front: the first 16 mm inside the front wall stay clear above the deck for gland nuts and cable bends.

Weather and vibration:
  - 3 mm walls, 3 mm floor, a 12 mm thick top band (45 degree chamfer under it, prints without supports).
  - Lid: 3 mm silicone foam cord in a groove on top of the wall, a tongue on the lid squeezes it 33 %. Fourteen M3 screws
    into heat-set inserts sit outside the cord, so no screw is a leak path. A skirt around the lid covers the seam.
    Ten snap clips (four per long side, one per short side, between the screws) are arms cut out of the skirt whose
    hooks catch under ledges in the band: the lid clicks shut and holds without the screws; the screws add the force.
  - Every opening sits low, under the band: probe glands in the rear wall, charge port, button and wheel sensor gland
    in the front wall, the camera ribbon slot (with a clamp plate) low in the +Y side wall, under the deck.
  - Rain hoods: a removable cover over each end wall's openings (roof, two cheeks, front face, open bottom), screwed
    through posts into blind inserts in the wall, so rain and spray never hit a gland or port directly and cables
    leave downwards. The ribbon clamp carries its own small visor.
  - Mount: the box screws onto a shoe (four M3 into blind floor bosses: no holes through the floor). The shoe slides
    along two dovetail rails on a rack plate and is locked by one M3 screw at the back. The rack plate is strapped to
    the rack with hose clamps or UV zip ties through a field of slots, so it suits any rail spacing.

Writes box_v2_body / _lid / _deck / _board_clamp / _shoe / _rack_plate / _ribbon_clamp / _rear_hood / _front_hood (.stl each, .step assembly) and
box_v2_plate*.3mf into --out. Stops with an error if a check fails.
"""
import argparse
import pathlib

import cadquery as cq

# ----------------------------------------------------------------------------- PARAMETERS (mm)
# box
IN_L, IN_W, IN_H = 216.0, 164.0, 78.0   # clear space inside (along bike, across, floor to lid underside)
IN_R = 6.0                              # inside corner radius (vertical edges)
WALL, FLOOR = 3.0, 3.0                  # wall and floor thickness
BAND_OUT, BAND_H = 9.0, 12.0            # top band: sticks out past the wall, height (inserts for the lid screws live in it)
# lid seal (3 mm silicone foam cord)
CORD = 3.0                              # cord diameter
GROOVE_W, GROOVE_D = 3.6, 3.0           # groove in the wall top
GROOVE_IN = 3.0                         # groove centre, measured outwards from the inside face of the wall
SQUEEZE = 0.33                          # cord compression when the lid is down
TONGUE_W = 2.8                          # tongue on the lid that presses the cord
LID_T, LID_RIB, SKIRT_H, SKIRT_T, SKIRT_CLR = 4.0, 4.0, 8.0, 2.0, 0.6
SCREW_IN = 8.4                          # lid screw centre, measured outwards from the inside face of the wall
SCREWS_X = (-88.0, -44.0, 0.0, 44.0, 88.0)   # lid screws along each long side
SCREWS_Y = (-40.0, 40.0)                # lid screws along each short side
INSERT_D, INSERT_DEPTH, CLEAR_D = 4.0, 7.0, 3.4   # M3 heat-set insert hole, its depth, M3 clearance hole
# snap clips: arms cut out of the lid skirt hook under a ledge in the band, so the lid holds without the screws
CLIP_W = 12.0                           # arm width
CLIP_L = 12.0                           # arm length, from the lid underside to its tip
CLIP_ENG = 0.7                          # how far the hook reaches into the band (the arm bends out this far)
CLIP_SLOT = 1.0                         # slot either side of the arm, frees it from the skirt
CLIP_FLAT = 0.6                         # straight part of the hook above its 45 degree lead-in ramp
CLIP_CLR = 0.3                          # recess in the band: deeper than the hook by this, and this much wider per side
CLIP_PLAY = 0.1                         # hook sits this far under the ledge with the lid down (cord takes it up)
CLIPS_LONG = (-66.0, -22.0, 22.0, 66.0)  # clip centres along each long side (between the screws)
CLIPS_SHORT = (0.0,)                    # clip centres along each short side
CLIP_STRAIN = 0.02                      # most bending strain allowed in the arm (ASA)
# deck and what holds it
COL = 14.0                              # column block size (corner columns are COL x COL, middle ones 12 x COL)
DECK_T, DECK_LIP_W, DECK_LIP_H = 3.0, 2.0, 4.0
GUTTER = 6.0                            # deck edge to inside wall: the cable gutter
END_KEEP = 16.0                         # kept clear above the deck inside the front wall (gland nuts, cable bends)
DECK_REAR = 74.0                        # the deck ends here (X); behind it the ultrasonic boards stand on the rear wall
FIT = 0.4                               # clearance per side in every pocket
POCKET_WALL = 2.4
TIE_SLOT = (4.4, 2.2)                   # zip-tie slot (along the tie width, across)
# electronics (ESTIMATE where noted; the rest from hardware/CLAUDE.md)
BANK = (152.0, 72.0, 27.0)              # UGREEN Nexode 20000 mAh 45 W: 152 x 72 measured by the user, thickness ESTIMATE
BANK_PAD = 2.0                          # foam pad between the bank and the deck
PI = (90.0, 61.0, 31.0)                 # Pi 5 in its case, lying flat (case height an estimate)
PI_PLUGS = 30.0                         # room in front of the Pi's USB end for plugs
BB = (87.0, 54.0, 10.0)                 # breadboard, lying flat
BB_WIRES = 25.0                         # jumper wires stand this high above it
IMU = (25.6, 22.7, 4.6)                 # BNO085
GPS = (50.0, 38.0, 20.0)                # USB GPS, cable out of the -X end
US = (42.0, 29.0, 1.2)                  # AJ-SR04M board: long side (stands vertical), short side, PCB. 42 x 29 x 18 overall (retailer spec)
US_N = 4
US_COMP = 6.0                           # parts on the board's front face stand this high (ESTIMATE: 18 overall = 6 + 1.2 + 11)
US_PLUG = (11.0, 12.0, 12.0)            # probe socket + plug on the back, sticking out x across x up, ESTIMATE
US_PLUG_OFF = (0.0, 0.0)                # plug centre from the board centre (across, up): the middle of the board
US_STRAIGHT = 4.0                       # straight probe cable between the plug and the gland nut
US_WIRE_GAP, US_MID_GAP = 10.0, 8.0     # gap where two headers face each other, gap between the pairs
US_SLOT = (1.9, 1.6)                    # slot for a board edge (width, depth)
LEDGE_Z = 18.0                          # top of the board ledge above the inside floor
CLAMP = (11.0, 7.0)                     # clamp bar (front to back, tall)
# end-wall openings
GLAND_D = 16.2                          # M16 gland hole
GLAND_NUT = (24.0, 6.0)                 # gland locknut across corners, thickness (inside the wall)
OPENING_Z = 38.0                        # height of every end-wall opening above the floor (inside)
FRONT_HOLES = ((-40.0, 16.2), (0.0, 16.2), (40.0, 16.2))   # front wall: USB-C charge port, power button, wheel sensor gland
RIBBON = (20.0, 3.0)                    # camera ribbon slot in the +Y side wall (along, up)
RIBBON_X, RIBBON_Z = 40.0, 15.0         # its centre: along the box, above the inside floor (under the deck)
RIBBON_PAD = (40.0, 16.0, 4.0)          # raised pad for the clamp (along, up, out)
RIBBON_SCREW = 16.0                     # clamp screws either side of the slot
# mount
BOSS_R, BOSS_H = 5.0, 6.0               # floor bosses for the shoe screws (inside)
BOSSES = ((-85.0, -46.0), (-85.0, 46.0), (85.0, -46.0), (85.0, 46.0))
SHOE = (190.0, 110.0, 10.0)
RAIL_Y = 28.0                           # dovetail rails at +-RAIL_Y
RAIL_BASE, RAIL_H = 8.0, 6.0            # dovetail width at the plate, height (45 degree flanks)
RAIL_CLR = 0.3
PLATE = (240.0, 150.0, 6.0)             # rack plate
LOCK_TAB = (8.0, 30.0, 12.0)            # tab at the back of the rack plate for the lock screw (thick, wide, tall)
STRAP_SLOT = (13.0, 3.5)                # slots for 12 mm hose clamps or zip ties (along X, across)
STRAP_X = (-95.0, 0.0, 90.0)
STRAP_PITCH = 7.0
DESICCANT = (50.0, 40.0, 12.0)          # cage under the lid for a silica gel bag
# rain hoods: a removable cover over each row of wall openings, open at the bottom so cables leave downwards
HOOD_D, HOOD_T = 38.0, 2.4              # how far it stands out from the wall, wall thickness
GLAND_OUT = 22.0                        # gland (or port) body outside the wall: dome + cable, ESTIMATE
HOOD_SIDE_DROP, HOOD_FRONT_DROP = 18.0, 10.0   # side cheeks and front face reach this far below the openings' centre
HOOD_POST_R = 5.0                       # posts inside the hood carry the screws to the wall
HOOD_ROOF_DROP = 4.0                    # the roof falls this much towards its front edge, so water runs off outwards
HOOD_SCREW_REAR = (0.0, -38.8, 38.8)    # Y of the rear hood screws (between the probe glands)
HOOD_SCREW_FRONT = (-20.0, 20.0)        # Y of the front hood screws (between the front holes)
HOOD_SCREW_LEN = 9.0                    # post left under the counterbore: an M3 x 16 reaches 7 mm into the insert
HOOD_FOAM = 1.0                         # foam strip between the wall and the back edges of each roof and cheek (seals the seam)
DRIP_IN, DRIP_W, DRIP_H = 1.5, 1.5, 1.0  # drip notch under the band: lip left at the edge, notch width, drip face height
RAIN_ANGLES = (0.0, 45.0)               # the build checks every opening is roofed against rain from straight above to this slant
E = 1.0                                 # boolean overshoot

# ----------------------------------------------------------------------------- derived
OUT_L, OUT_W = IN_L + 2 * WALL, IN_W + 2 * WALL
BODY_H = FLOOR + IN_H
HX, HY = IN_L / 2, IN_W / 2              # inside half sizes
Z0 = FLOOR                               # inside floor
COL_TOP = Z0 + BANK[2] + FIT + BANK_PAD  # deck underside
DECK_Z = COL_TOP + DECK_T                # deck top
X_FRONT, X_REAR = -HX + END_KEEP, DECK_REAR - DECK_LIP_W - 2.0   # items on the deck stay between these
YU = HY - GUTTER                         # and within +-YU
DECK_FRONT = -HX + GUTTER
TONGUE_H = GROOVE_D - CORD * (1 - SQUEEZE)
HOOD_TOP = BODY_H - BAND_H - BAND_OUT - 0.5   # hood roof stays under the band chamfer
HOOD_SCREW_Z = HOOD_TOP - HOOD_ROOF_DROP - HOOD_T - HOOD_POST_R + 1.0


def pocket(part):
    return part[0] + 2 * (FIT + POCKET_WALL), part[1] + 2 * (FIT + POCKET_WALL)


GPS_FP = (GPS[1], GPS[0])                                       # GPS turned 90 degrees: cable end towards -Y (the lane)
PI_O, BB_O, IMU_O, GPS_O = pocket(PI), pocket(BB), pocket(IMU), pocket(GPS_FP)
# deck row A (+Y): Pi, room for its USB plugs, spare bay;  row B (-Y): breadboard, GPS
PI_C = (X_FRONT + PI_O[0] / 2, YU - PI_O[1] / 2)
BB_C = (X_FRONT + BB_O[0] / 2, -YU + BB_O[1] / 2)
GPS_C = (X_REAR - GPS_O[0] / 2, -YU + GPS_O[1] / 2)
SPARE = (PI_C[0] + PI_O[0] / 2 + PI_PLUGS, X_REAR)            # spare bay in row A (X from, to)
# ultrasonic boards on the rear wall: plug -> straight cable -> gland nut -> wall
US_BACK = HX - GLAND_NUT[1] - US_STRAIGHT - US_PLUG[0]        # X of each board's back face
US_FRONT = US_BACK - US[2]
US_SW = US[1] + 2 * FIT                                       # slot width for a board
US_BOT = Z0 + LEDGE_Z - US_SLOT[1]                            # board bottom edge (in its slot)
US_ZC = US_BOT + US[0] / 2
_span = US_N * US_SW + 2 * US_WIRE_GAP + US_MID_GAP
US_Y = []                                                     # board centres, and which side each header faces
_y = -_span / 2
for _i in range(US_N):
    US_Y.append(_y + US_SW / 2)
    _y += US_SW + (US_MID_GAP if _i == 1 else US_WIRE_GAP)
US_HDR = [1, -1, 1, -1]
US_PLUG_C = [(y + US_PLUG_OFF[0], US_ZC + US_PLUG_OFF[1]) for y in US_Y]   # gland centres (Y, Z)
LEDGE_X = US_FRONT - US_COMP - 1.0                            # front of the ledge and the clamp bar
CLAMP_Z = US_BOT + US[0] + 0.4 - (US_SLOT[1] + 0.8)           # clamp bar underside
POST_Y = _span / 2 + 0.6                                      # end posts for the clamp bar start here
POST_C = ((LEDGE_X + LEDGE_X + CLAMP[0]) / 2, (POST_Y + HY) / 2)
# floor: the IMU sits beside the power bank, fixed to the box itself (no screws through the floor: tape or silicone)
IMU_C = (30.0, -(BANK[1] / 2 + FIT + POCKET_WALL + 3.0 + IMU_O[1] / 2))
LANE = (BB_C[1] + BB_O[1] / 2, PI_C[1] - PI_O[1] / 2)           # cable lane between the rows (Y from, to)
LANE_Y = sum(LANE) / 2
BANK_C = (0.0, 0.0)                                             # power bank on the floor, ports towards -X
COLUMNS = [(x, sy * (HY - COL / 2)) for x in (-(HX - COL / 2), 0.0, DECK_REAR - 8.0) for sy in (-1, 1)]
LID_SCREWS = [(x, s * (HY + WALL + SCREW_IN - WALL)) for x in SCREWS_X for s in (-1, 1)]
LID_SCREWS += [(s * (HX + SCREW_IN), y) for y in SCREWS_Y for s in (-1, 1)]
BAND_FACE = WALL + BAND_OUT                                     # band outer face, outwards of the inside face of the wall
SKIRT_IN = BAND_FACE + SKIRT_CLR                                # skirt inner face
CLIP_TIP = BODY_H - CLIP_L
CLIP_HOOK = SKIRT_CLR + CLIP_ENG                                # hook sticks out of the arm this far (and its ramp is this tall)
CLIP_CATCH = CLIP_TIP + CLIP_HOOK + CLIP_FLAT                   # hook top face, the one that catches
# (angle, half size, position along the side): the clip is built on the +X side and turned into place
CLIPS = [(a, HY, t) for a in (90, 270) for t in CLIPS_LONG] + [(a, HX, t) for a in (0, 180) for t in CLIPS_SHORT]


# ----------------------------------------------------------------------------- helpers
def rbox(lx, ly, r, z0, h, cx=0.0, cy=0.0):
    b = cq.Workplane("XY").box(lx, ly, h, centered=(True, True, False)).translate((cx, cy, z0))
    return b.edges("|Z").fillet(r) if r > 0 else b


def box(lx, ly, h, cx, cy, z0):
    return cq.Workplane("XY").box(lx, ly, h, centered=(True, True, False)).translate((cx, cy, z0))


def cyl(r, h, cx, cy, z0):
    return cq.Workplane("XY").circle(r).extrude(h).translate((cx, cy, z0))


def xhole(r, x0, length, y, z):
    """Cylinder along +X from x0."""
    return cq.Workplane("YZ").circle(r).extrude(length).translate((x0, y, z))


def yhole(r, y0, length, x, z):
    """Cylinder along +Y from y0."""
    return cq.Workplane("XZ").circle(r).extrude(-length).translate((x, y0, z))


def ring(off_in, off_out, z0, h):
    """Band around the inside outline, from off_in to off_out outwards of the inside face of the wall."""
    outer = rbox(IN_L + 2 * off_out, IN_W + 2 * off_out, IN_R + off_out, z0, h)
    inner = rbox(IN_L + 2 * off_in, IN_W + 2 * off_in, IN_R + off_in, z0 - E, h + 2 * E)
    return outer.cut(inner)


def on_side(solid, ang, half, t):
    """Move a solid built at x = offset outwards of the inside face of the +X wall (y = 0) to its place round the box."""
    return solid.translate((half, t, 0)).rotate((0, 0, 0), (0, 0, 1), ang)


def profile(pts, width):
    """Closed (offset, z) outline, extruded `width` across, centred on y = 0."""
    return cq.Workplane("XZ").polyline(pts).close().extrude(width / 2, both=True)


def clip_arm():
    """Snap arm in profile: hangs from the lid outside the band, a hook at its tip with a 45 degree lead-in."""
    so, st = SKIRT_IN, SKIRT_IN + SKIRT_T
    hook = BAND_FACE - CLIP_ENG
    return profile([(so, BODY_H + E), (so, CLIP_CATCH), (hook, CLIP_CATCH), (hook, CLIP_TIP + CLIP_HOOK),
                    (so, CLIP_TIP), (st, CLIP_TIP), (st, BODY_H + E)], CLIP_W)


def clip_recess():
    """Ledge in the band for the hook: open downwards into the band chamfer, flat ceiling 1 mm deep (prints fine)."""
    d = CLIP_ENG + CLIP_CLR
    z0 = BODY_H - BAND_H - d                    # where the 45 degree chamfer is exactly d in from the band face
    return profile([(BAND_FACE - d, z0), (BAND_FACE + E, z0), (BAND_FACE + E, CLIP_CATCH + CLIP_PLAY),
                    (BAND_FACE - d, CLIP_CATCH + CLIP_PLAY)], CLIP_W + 2 * CLIP_CLR)


def clip_strain():
    """Peak bending strain in the arm when the hook rides over the band (cantilever, load at the hook's middle)."""
    arm = BODY_H - (CLIP_TIP + CLIP_CATCH) / 2
    return 1.5 * SKIRT_T * CLIP_ENG / arm ** 2


def walls_of(outer_l, outer_w, inner_l, inner_w, h, cx, cy, z0, open_side=None, gap=0.0):
    w = box(outer_l, outer_w, h, cx, cy, z0).cut(box(inner_l, inner_w, h + 2 * E, cx, cy, z0 - E))
    if open_side:  # cut an opening `gap` wide in one side: '-x', '+x', '-y', '+y'
        s = 1 if open_side[0] == "+" else -1
        if open_side[1] == "x":
            w = w.cut(box(outer_l, gap, h + 2 * E, cx + s * outer_l / 2, cy, z0 - E))
        else:
            w = w.cut(box(gap, outer_w, h + 2 * E, cx, cy + s * outer_w / 2, z0 - E))
    return w


def tie_pair(cx, cy, span, along="y"):
    """Two zip-tie slots `span` apart; a tie goes down one, under the deck, and up the other."""
    a, b = TIE_SLOT
    if along == "y":  # tie runs across Y (holds something lying along X)
        return box(a, b, 3 * DECK_T, cx, cy - span / 2, COL_TOP - E).union(box(a, b, 3 * DECK_T, cx, cy + span / 2, COL_TOP - E))
    return box(b, a, 3 * DECK_T, cx - span / 2, cy, COL_TOP - E).union(box(b, a, 3 * DECK_T, cx + span / 2, cy, COL_TOP - E))


# ----------------------------------------------------------------------------- body
def body():
    b = rbox(OUT_L, OUT_W, IN_R + WALL, 0, BODY_H)
    # top band with a 45 degree chamfer under it
    band = rbox(IN_L + 2 * (WALL + BAND_OUT), IN_W + 2 * (WALL + BAND_OUT), IN_R + WALL + BAND_OUT, BODY_H - BAND_H - BAND_OUT, BAND_H + BAND_OUT)
    band = band.faces("<Z").chamfer(BAND_OUT - 0.01)
    b = b.union(band)
    b = b.cut(rbox(IN_L, IN_W, IN_R, Z0, IN_H + E))
    # columns for the deck: corner blocks fill the corners, middle blocks sit on the long walls
    for cx, cy in COLUMNS:
        front = cx < -HX / 2   # front corner blocks also reach the front wall
        b = b.union(box(COL + (E if front else 0), COL + E, COL_TOP - Z0 + E, cx - (E / 2 if front else 0), cy + (E / 2 if cy > 0 else -E / 2), Z0 - E))
        b = b.cut(cyl(INSERT_D / 2, INSERT_DEPTH + E, cx, cy, COL_TOP - INSERT_DEPTH))
    # power bank cradle: long sides and the +X end, open at -X for the cables
    bo = pocket(BANK)
    b = b.union(walls_of(bo[0], bo[1], BANK[0] + 2 * FIT, BANK[1] + 2 * FIT, 10.0, *BANK_C, Z0 - E / 2, "-x", BANK[1] + 2 * FIT))
    # IMU pocket on the floor, cable openings at both ends
    b = b.union(walls_of(*IMU_O, IMU[0] + 2 * FIT, IMU[1] + 2 * FIT, 4.0 + E, *IMU_C, Z0 - E, "-x", 9.0)
                .cut(box(IMU_O[0] / 2, 9.0, 6.0, IMU_C[0] + IMU_O[0] / 2, IMU_C[1], Z0)))
    # floor bosses for the shoe screws: blind holes from below
    for x, y in BOSSES:
        b = b.union(cyl(BOSS_R, BOSS_H + E, x, y, Z0 - E))
        b = b.cut(cyl(INSERT_D / 2, INSERT_DEPTH + E, x, y, -E))
    # lid seal groove and lid screw inserts
    b = b.cut(ring(GROOVE_IN - GROOVE_W / 2, GROOVE_IN + GROOVE_W / 2, BODY_H - GROOVE_D, GROOVE_D + E))
    for x, y in LID_SCREWS:
        b = b.cut(cyl(INSERT_D / 2, INSERT_DEPTH + E, x, y, BODY_H - INSERT_DEPTH))
    for c in CLIPS:   # ledges for the lid's snap clips
        b = b.cut(on_side(clip_recess(), *c))
    # drip notch all round under the band: water creeping along the chamfer drops off here instead of reaching the wall
    n1, n2 = BAND_FACE - DRIP_IN - DRIP_W, BAND_FACE - DRIP_IN
    zt = BODY_H - BAND_H - DRIP_IN + DRIP_H
    zl = BODY_H - BAND_H - (BAND_FACE - n1) - 1.0
    b = b.cut(ring(n1, n2, zl, zt - zl))
    # rear wall: board ledge (45 degree underside), end posts for the clamp bar, one gland straight behind each plug
    b = b.union(board_ledge())
    for y, z in US_PLUG_C:
        b = b.cut(xhole(GLAND_D / 2, HX - E, WALL + 2 * E, y, z))
    # camera ribbon: slot low in the +Y side wall with a raised pad and two inserts for the clamp plate
    pw, ph, pt = RIBBON_PAD
    rz = Z0 + RIBBON_Z
    b = b.union(box(pw, pt + E, ph, RIBBON_X, HY + WALL + (pt - E) / 2, rz - ph / 2))
    b = b.cut(box(RIBBON[0], WALL + pt + 2 * E, RIBBON[1], RIBBON_X, HY + (WALL + pt) / 2, rz - RIBBON[1] / 2))
    for s in (-1, 1):
        b = b.cut(yhole(INSERT_D / 2, HY + 1.0, WALL + pt, RIBBON_X + s * RIBBON_SCREW, rz))
    # front wall
    zc = Z0 + OPENING_Z
    for y, d in FRONT_HOLES:
        b = b.cut(xhole(d / 2, -HX - WALL - E, WALL + 2 * E, y, zc))
    # rain hood screws: blind inserts from outside into bosses on the inside of the end walls (no hole through)
    for sx, ys in ((1, HOOD_SCREW_REAR), (-1, HOOD_SCREW_FRONT)):
        for y in ys:
            b = b.union(hood_boss(sx, y))
            x0 = sx * (HX + WALL)
            b = b.cut(xhole(INSERT_D / 2, x0 - INSERT_DEPTH if sx > 0 else x0 - E, INSERT_DEPTH + E, y, HOOD_SCREW_Z))
    return b


def hood_boss(sx, y):
    """Boss on the inside of an end wall, 6 mm deep, 45 degree underside."""
    z = HOOD_SCREW_Z
    prof = [(HX + E, z + 4.0), (HX - 6.0, z + 4.0), (HX - 6.0, z - 4.0), (HX, z - 10.0), (HX + E, z - 10.0)]
    bo = cq.Workplane("XZ").polyline(prof).close().extrude(4.0, both=True).translate((0, y, 0))
    return bo if sx > 0 else bo.mirror("YZ")


def hood(sx):
    """Rain hood over the rear (sx = 1) or front (sx = -1) openings: top, two cheeks, front face, open bottom."""
    if sx > 0:
        ys, zc, w = HOOD_SCREW_REAR, US_ZC, 2 * (max(abs(y) for y, _ in US_PLUG_C) + GLAND_NUT[0] / 2 + 4.0)
    else:
        ys, zc, w = HOOD_SCREW_FRONT, Z0 + OPENING_Z, 2 * (max(abs(y) for y, _ in FRONT_HOLES) + GLAND_NUT[0] / 2 + 4.0)
    # roof, cheeks and front stand HOOD_FOAM off the wall (a foam strip seals that seam); the posts sit on the wall
    xw = HX + WALL
    x0, x1 = xw + HOOD_FOAM, xw + HOOD_FOAM + HOOD_D
    top, front_top = HOOD_TOP, HOOD_TOP - HOOD_ROOF_DROP

    def prism(pts, width, y):
        return cq.Workplane("XZ").polyline(pts).close().extrude(width / 2, both=True).translate((0, y, 0))
    h = prism([(x0, top), (x1, front_top), (x1, front_top - HOOD_T), (x0, top - HOOD_T)], w, 0)        # sloped roof
    zb = zc - HOOD_SIDE_DROP
    for s in (-1, 1):
        h = h.union(prism([(x0, top), (x1, front_top), (x1, zb), (x0, zb)], HOOD_T, s * (w / 2 - HOOD_T / 2)))
    h = h.union(box(HOOD_T, w, front_top - (zc - HOOD_FRONT_DROP), x1 - HOOD_T / 2, 0, zc - HOOD_FRONT_DROP))
    for y in ys:
        h = h.union(xhole(HOOD_POST_R, xw, x1 - xw - 0.01, y, HOOD_SCREW_Z))   # meets the roof towards the front
        h = h.cut(xhole(CLEAR_D / 2, xw - E, x1 - xw + 2 * E, y, HOOD_SCREW_Z))
        h = h.cut(xhole(3.25, xw + HOOD_SCREW_LEN, x1 - xw, y, HOOD_SCREW_Z))   # counterbore from the front
    return h if sx > 0 else h.mirror("YZ")


def board_ledge():
    top = Z0 + LEDGE_Z
    w = 2 * (HY + 0.3)
    prof = [(LEDGE_X, top), (HX + 0.3, top), (HX + 0.3, Z0 - 0.5), (LEDGE_X + (top - 4.0 - Z0) + 0.5, Z0 - 0.5), (LEDGE_X, top - 4.0)]
    led = cq.Workplane("XZ").polyline(prof).close().extrude(w / 2, both=True)
    for y in US_Y:
        led = led.cut(box(US_SLOT[0], US_SW, US_SLOT[1] + E, US_FRONT + US[2] / 2, y, top - US_SLOT[1]))
    for s in (-1, 1):  # end posts up to the clamp bar, insert in the top
        cy = s * POST_C[1]
        post = box(CLAMP[0], HY + 0.3 - POST_Y, CLAMP_Z - top + E, POST_C[0], s * (POST_Y + HY + 0.3) / 2, top - E)
        led = led.union(post).cut(cyl(INSERT_D / 2, INSERT_DEPTH + E, POST_C[0], cy, CLAMP_Z - INSERT_DEPTH))
    return led


def board_clamp():
    """Bar across the tops of the boards, two M3 into the end posts."""
    bar = box(CLAMP[0], 2 * (HY - 0.3), CLAMP[1], POST_C[0], 0, CLAMP_Z)
    for y in US_Y:
        bar = bar.cut(box(US_SLOT[0], US_SW, US_SLOT[1] + 0.8 + E, US_FRONT + US[2] / 2, y, CLAMP_Z - E))
    for s in (-1, 1):
        bar = bar.cut(cyl(CLEAR_D / 2, CLAMP[1] + 2 * E, POST_C[0], s * POST_C[1], CLAMP_Z - E))
    return bar


# ----------------------------------------------------------------------------- lid (as fitted; printed top face down)
def lid():
    so = WALL + BAND_OUT + SKIRT_CLR          # skirt inside face, clear of the band
    off = so + SKIRT_T
    l = rbox(IN_L + 2 * off, IN_W + 2 * off, IN_R + off, BODY_H, LID_T)
    l = l.union(ring(so, off, BODY_H - SKIRT_H, SKIRT_H + LID_T / 2))
    # snap clips: a slot either side frees an arm from the skirt, the arm runs on below it to a hook
    for c in CLIPS:
        for s in (-1, 1):
            slot = box(SKIRT_T + 2.0, CLIP_SLOT, SKIRT_H + E, so + SKIRT_T / 2, s * (CLIP_W + CLIP_SLOT) / 2, BODY_H - SKIRT_H - E)
            l = l.cut(on_side(slot, *c))
        l = l.union(on_side(clip_arm(), *c))
    # tongue presses the cord
    l = l.union(ring(GROOVE_IN - TONGUE_W / 2, GROOVE_IN + TONGUE_W / 2, BODY_H - TONGUE_H, TONGUE_H + E))
    # stiffening ribs and the desiccant cage, all inside the inner outline
    z = BODY_H - LID_RIB
    for x in (-78.0, -26.0, 26.0, 78.0):
        l = l.union(box(2.0, IN_W - 2.0, LID_RIB + E, x, 0, z))
    l = l.union(box(IN_L - 2.0, 2.0, LID_RIB + E, 0, 0, z))
    dl, dw, dh = DESICCANT
    l = l.union(walls_of(dl + 3.2, dw + 3.2, dl, dw, dh + E, *GPS_C, BODY_H - dh, "-x", dw - 10))
    # 45 degree lips on the open end of the cage keep the bag in (printable: lid prints upside down)
    for s in (-1, 1):
        lip = (cq.Workplane("YZ").polyline([(-0.5, 0), (1.6, 0), (-0.5, 2.1)]).close().extrude(dl)
               .translate((GPS_C[0] - dl / 2, 0, 0)))
        lip = lip.mirror("XZ") if s > 0 else lip
        l = l.union(lip.translate((0, GPS_C[1] + s * dw / 2, BODY_H - dh)))
    for x, y in LID_SCREWS:
        l = l.cut(cyl(CLEAR_D / 2, LID_T + 2 * E, x, y, BODY_H - E))
    return l


# ----------------------------------------------------------------------------- deck
def deck():
    dl, dw, dc = DECK_REAR - DECK_FRONT, IN_W - 2 * GUTTER, (DECK_REAR + DECK_FRONT) / 2
    d = rbox(dl, dw, IN_R, COL_TOP, DECK_T, dc)
    for cx, cy in COLUMNS:  # ears reach out over the columns
        d = d.union(cyl(5.0, DECK_T, cx, cy, COL_TOP))
    lip = rbox(dl, dw, IN_R, DECK_Z - E, DECK_LIP_H + E, dc).cut(rbox(dl - 2 * DECK_LIP_W, dw - 2 * DECK_LIP_W, IN_R - DECK_LIP_W, DECK_Z - 2 * E, DECK_LIP_H + 3 * E, dc))
    d = d.union(lip)
    # Pi: four corner brackets (low, so the case's ports stay free) and two straps
    px, py = PI[0] + 2 * FIT, PI[1] + 2 * FIT
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = PI_C[0] + sx * (px / 2 + POCKET_WALL / 2), PI_C[1] + sy * (py / 2 + POCKET_WALL / 2)
            d = d.union(box(POCKET_WALL, 12.0, 5.0 + E, cx, cy - sy * 4.8, DECK_Z - E))
            d = d.union(box(12.0, POCKET_WALL, 5.0 + E, cx - sx * 4.8, cy, DECK_Z - E))
    # breadboard tray, GPS cradle (cable out of the +Y end, into the lane)
    d = d.union(walls_of(*BB_O, BB[0] + 2 * FIT, BB[1] + 2 * FIT, 5.0 + E, *BB_C, DECK_Z - E))
    d = d.union(walls_of(*GPS_O, GPS_FP[0] + 2 * FIT, GPS_FP[1] + 2 * FIT, 10.0 + E, *GPS_C, DECK_Z - E, "+y", 14.0))
    # cable pass-down to the bank, zip-tie anchors
    d = d.cut(box(30.0, 10.0, 3 * DECK_T, -55.0, LANE_Y, COL_TOP - E))
    for x in (-75.0, -30.0, 0.0, 35.0, 65.0):
        d = d.cut(tie_pair(x, LANE_Y, LANE[1] - LANE[0] - 5.0))
    for dx in (-25.0, 25.0):
        d = d.cut(tie_pair(PI_C[0] + dx, PI_C[1], py + 2 * POCKET_WALL + 4.0))
    d = d.cut(tie_pair(GPS_C[0], GPS_C[1] - 8.0, GPS_O[0] + 4.0, along="x"))
    for x in (SPARE[0] + 8.0, SPARE[1] - 8.0):   # spare bay: tie points for a future board
        for y in (PI_C[1] - 20.0, PI_C[1] + 20.0):
            d = d.cut(tie_pair(x, y, 16.0))
    d = d.cut(tie_pair(BB_C[0], BB_C[1], BB_O[1] + 4.0))
    for cx, cy in COLUMNS:
        d = d.cut(cyl(CLEAR_D / 2, DECK_T + 2 * E, cx, cy, COL_TOP - E))
    return d


# ----------------------------------------------------------------------------- mount
def dovetail(length, base, h, x0, y, z0, grow=0.0):
    """Trapezoid prism along X: `base` wide at z0, base + 2h wide at z0 + h (45 degree flanks)."""
    b, t = base / 2 + grow, base / 2 + h + grow
    return (cq.Workplane("YZ").polyline([(-b, 0), (b, 0), (t, h), (-t, h)]).close().extrude(length)
            .translate((x0, y, z0)))


def shoe():
    sl, sw, st = SHOE
    s = box(sl, sw, st, 0, 0, -st)
    for sy in (-1, 1):
        s = s.cut(dovetail(sl + 2 * E, RAIL_BASE, RAIL_H + RAIL_CLR, -sl / 2 - E, sy * RAIL_Y, -st - 0.01, RAIL_CLR))
    for x, y in BOSSES:
        s = s.cut(cyl(CLEAR_D / 2, st + 2 * E, x, y, -st - E)).cut(cyl(3.25, 3.5 + E, x, y, -st - E))
    s = s.cut(xhole(INSERT_D / 2, sl / 2 - INSERT_DEPTH, INSERT_DEPTH + E, 0, -st + 5.0))  # lock screw insert
    return s


def rack_plate():
    pl, pw, pt = PLATE
    top = -SHOE[2]
    p = box(pl, pw, pt, 0, 0, top - pt)
    for sy in (-1, 1):
        p = p.union(dovetail(pl - LOCK_TAB[0], RAIL_BASE, RAIL_H, -pl / 2, sy * RAIL_Y, top - 0.01))
    tx = SHOE[0] / 2 + LOCK_TAB[0] / 2
    p = p.union(box(LOCK_TAB[0], LOCK_TAB[1], LOCK_TAB[2] + 0.01, tx, 0, top - 0.01))
    p = p.cut(xhole(CLEAR_D / 2, tx - LOCK_TAB[0] / 2 - E, LOCK_TAB[0] + 2 * E, 0, top + 5.0))
    rail_zone = RAIL_Y + RAIL_BASE / 2 + RAIL_H + 2.0
    ys, y = [], -pw / 2 + 6.0
    while y <= pw / 2 - 6.0:
        if abs(abs(y) - RAIL_Y) > rail_zone - RAIL_Y:
            ys.append(y)
        y += STRAP_PITCH
    for x in STRAP_X:
        for y in ys:
            p = p.cut(box(*STRAP_SLOT, pt + 2 * E, x, y, top - pt - E))
    return p


def ribbon_clamp():
    pw, ph, pt = RIBBON_PAD
    rz, y0 = Z0 + RIBBON_Z, HY + WALL + pt + 1.0   # 1 mm foam between pad and clamp
    zb = rz + ph / 2 + 0.4                         # visor roof underside, clear of the pad top
    c = box(pw, 4.0, zb - (rz - ph / 2) + 0.01, RIBBON_X, y0 + 2.0, rz - ph / 2)
    c = c.cut(box(RIBBON[0], 6.0, RIBBON[1], RIBBON_X, y0 + 2.0, rz - RIBBON[1] / 2))
    for s in (-1, 1):
        c = c.cut(yhole(CLEAR_D / 2, y0 - E, 4.0 + 2 * E, RIBBON_X + s * RIBBON_SCREW, rz))
    # visor: a roof from the wall (foam strip in the seam) over the pad and clamp to 12 mm out, falling outwards,
    # and two cheeks, open below, so rain cannot run down onto the slot or sit on the pad
    yb, yf = HY + WALL + HOOD_FOAM, y0 + 4.0 + 12.0
    c = c.union(cq.Workplane("YZ").polyline([(yb, zb), (yf, zb), (yf, zb + HOOD_T), (yb, zb + HOOD_T + 1.5)]).close()
                .extrude(pw / 2, both=True).translate((RIBBON_X, 0, 0)))
    for s in (-1, 1):
        c = c.union(box(HOOD_T, 12.0, zb - (rz - ph / 2) + 0.01, RIBBON_X + s * (pw / 2 - HOOD_T / 2), y0 + 4.0 + 6.0 - 0.01, rz - ph / 2))
    return c


# ----------------------------------------------------------------------------- dummies (fit checks)
def dummies():
    z = DECK_Z
    d = {
        "power bank": box(*BANK[:2], BANK[2], *BANK_C, Z0),
        "Pi 5 case": box(*PI[:2], PI[2], *PI_C, z),
        "breadboard + wires": box(*BB[:2], BB[2] + BB_WIRES, *BB_C, z),
        "IMU": box(*IMU[:2], IMU[2], *IMU_C, Z0),
        "GPS": box(*GPS_FP, GPS[2], *GPS_C, z),
    }
    for i, (y, (py, pz)) in enumerate(zip(US_Y, US_PLUG_C)):
        n = f"ultrasonic board {i + 1}"
        b = box(US[2], US[1], US[0], US_FRONT + US[2] / 2, y, US_BOT)
        b = b.union(box(US_COMP, US[1] - 4.0, US[0] - 6.0, US_FRONT - US_COMP / 2, y, US_BOT + 3.0))   # parts on the front
        b = b.union(box(US_PLUG[0], US_PLUG[1], US_PLUG[2], US_BACK + US_PLUG[0] / 2, py, pz - US_PLUG[2] / 2))
        b = b.union(xhole(2.5, US_BACK + US_PLUG[0], US_STRAIGHT, py, pz))                              # straight probe cable
        d[n] = b
        hy = y + US_HDR[i] * (US[1] / 2 + US_WIRE_GAP / 4)   # soldered header wires, half the shared gap each
        d[n + " wires"] = box(10.0, US_WIRE_GAP / 2 - 0.2, 16.0, US_BACK - 6.0, hy, US_ZC - 8.0)
        d[f"rear gland nut {i + 1}"] = xhole(GLAND_NUT[0] / 2, HX - GLAND_NUT[1], GLAND_NUT[1], py, pz)
        d[f"rear gland outside {i + 1}"] = xhole(GLAND_NUT[0] / 2, HX + WALL, GLAND_OUT, py, pz)
    zc = Z0 + OPENING_Z
    for y, _ in FRONT_HOLES:
        d[f"front nut y={y:g}"] = xhole(GLAND_NUT[0] / 2, -HX, GLAND_NUT[1], y, zc)
        d[f"front part outside y={y:g}"] = xhole(GLAND_NUT[0] / 2, -HX - WALL - GLAND_OUT, GLAND_OUT, y, zc)
    return d


def keepouts():
    """Volumes the deck items must stay out of: cable zones at both end walls, Pi USB plugs, the cable lane."""
    z = DECK_Z + DECK_LIP_H
    k = {"front zone": box(END_KEEP, IN_W, IN_H, -HX + END_KEEP / 2, 0, z),
         "rear board zone": box(HX - DECK_REAR, IN_W, IN_H, (HX + DECK_REAR) / 2, 0, z)}
    k["Pi USB plugs"] = box(PI_PLUGS - 1.0, PI[1], PI[2], PI_C[0] + PI_O[0] / 2 + PI_PLUGS / 2, PI_C[1], z)
    k["cable lane"] = box(X_REAR - X_FRONT, LANE[1] - LANE[0] - 1.0, 20.0, (X_REAR + X_FRONT) / 2, LANE_Y, z)
    return k


# ----------------------------------------------------------------------------- checks
def vol(a, b):
    return sum(s.Volume() for s in a.intersect(b).solids().vals())


def rain_check(parts):
    """Rays from just outside every opening up into the rain (straight down and slanted towards the wall, per RAIN_ANGLES)
    must hit the box, lid, a hood or the ribbon visor. Returns the rays that get through."""
    import math
    covers = [parts[n].val() for n in ("body", "lid", "rear hood", "front hood", "ribbon clamp")]

    def blocked(p, d):
        return any(c.facesIntersectedByLine(cq.Vector(*p), cq.Vector(*d), direction="AlongAxis") for c in covers)

    def steps(a0, a1, n):
        return [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]
    assert not blocked((HX + WALL + HOOD_FOAM + HOOD_D + 5.0, 0, BODY_H / 2), (0, 0, 1)), "rain check sees nothing"
    pt = RIBBON_PAD[2]
    rays = []
    for ang in RAIN_ANGLES:
        s, c = math.sin(math.radians(ang)), math.cos(math.radians(ang))
        for sx, ops in ((1, US_PLUG_C), (-1, [(y, Z0 + OPENING_Z) for y, _ in FRONT_HOLES])):
            for y, z in ops:   # over the gland or port body outside the wall
                for xo in steps(0.2, GLAND_OUT, 6):
                    for yy in steps(y - GLAND_NUT[0] / 2, y + GLAND_NUT[0] / 2, 5):
                        p = (sx * (HX + WALL + xo), yy, z + GLAND_NUT[0] / 2)
                        if not blocked(p, (sx * s, 0, c)):
                            rays.append((ang, p))
        for xx in steps(RIBBON_X - RIBBON[0] / 2, RIBBON_X + RIBBON[0] / 2, 5):   # over the slot, pad and clamp
            for yo in steps(0.2, pt + 1.0 + 4.0, 5):
                p = (xx, HY + WALL + yo, Z0 + RIBBON_Z + RIBBON[1] / 2)
                if not blocked(p, (0, s, c)):
                    rays.append((ang, p))
    return rays


def check(parts):
    for name, p in parts.items():
        assert len(p.solids().vals()) == 1, f"{name}: {len(p.solids().vals())} solids, expected 1"
        assert p.val().isValid(), f"{name}: invalid shape"
    dm = dummies()
    for pname, p in parts.items():
        for dname, d in dm.items():
            v = vol(p, d)
            assert v < 0.05, f"{dname} overlaps {pname} ({v:.1f} mm3)"
    names = list(dm)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert vol(dm[a], dm[b]) < 0.05, f"{a} overlaps {b}"
    items = [n for n in names if "nut" not in n and "ultrasonic" not in n and n not in ("power bank", "IMU")]
    for kname, k in keepouts().items():
        for n in items:
            assert vol(dm[n], k) < 0.05, f"{n} sits in the {kname}"
    pairs = [("body", "lid"), ("body", "deck"), ("body", "shoe"), ("shoe", "rack plate"), ("body", "ribbon clamp"), ("lid", "deck"),
             ("body", "board clamp"), ("lid", "board clamp"), ("deck", "board clamp"),
             ("body", "rear hood"), ("body", "front hood"), ("lid", "rear hood"), ("lid", "front hood"),
             ("rack plate", "rear hood"), ("rack plate", "front hood"), ("body", "ribbon clamp")]
    assert HOOD_D >= GLAND_OUT + 8.0, "hood too shallow for the glands and a cable bend"
    for a, b in pairs:
        v = vol(parts[a], parts[b])
        assert v < 0.05, f"{a} and {b} overlap ({v:.1f} mm3)"
    # the deck lifts out past the columns' neighbours, and the bank sits under the deck with room for the pad
    assert BANK[2] + Z0 + FIT + BANK_PAD <= COL_TOP + 1e-6
    assert DECK_Z + max(PI[2], BB[2] + BB_WIRES, GPS[2]) <= BODY_H - LID_RIB - 2.0, "too tall for the lid ribs"
    assert CLAMP_Z + CLAMP[1] <= BODY_H - LID_RIB - 2.0, "clamp bar too close to the lid"
    for y, z in US_PLUG_C:   # the deck lifts out past the boards, the plug sits on the gland axis, the hex clears the band
        assert z + GLAND_NUT[0] / 2 <= BODY_H - BAND_H - BAND_OUT + 0.5, "probe gland hex hits the band chamfer"
        assert abs(y) + GLAND_NUT[0] / 2 <= HY + WALL - (IN_R + WALL) + WALL, "probe gland off the flat of the wall"
    assert DECK_REAR <= LEDGE_X - 4.0, "deck too close to the boards"
    pw = POST_C[1] - POST_Y
    assert pw - INSERT_D / 2 >= 1.6, f"clamp post insert wall {pw - INSERT_D / 2:.1f} mm"
    assert 0.25 <= SQUEEZE <= 0.45 and TONGUE_H > 0
    gap = (SCREW_IN - INSERT_D / 2) - (GROOVE_IN + GROOVE_W / 2)
    assert gap >= 1.2, f"insert too close to the groove ({gap:.2f} mm)"
    assert SCREW_IN + INSERT_D / 2 + 1.2 <= WALL + BAND_OUT, "insert breaks out of the band"
    # snap clips: arm strain, on the flat of the wall, clear of the screws, ledge above the band chamfer
    assert clip_strain() <= CLIP_STRAIN, f"clip arm strain {clip_strain() * 100:.1f} %"
    assert CLIP_TIP >= BODY_H - BAND_H - 1e-6, "clip hook below the band's flat face"
    assert CLIP_CATCH + CLIP_PLAY <= BODY_H - SKIRT_H - 1.0, "clip ledge hidden under the skirt"
    for ang, half, t in CLIPS:
        side = (HY if half == HX else HX) - IN_R   # flat part of this side, measured from its middle
        assert abs(t) + CLIP_W / 2 + CLIP_SLOT <= side, f"clip at {t} runs onto the corner"
        for x, y in LID_SCREWS:
            along, across = (y, x) if ang in (0, 180) else (x, y)
            if across * {0: 1, 90: 1, 180: -1, 270: -1}[ang] > 0:
                d = abs(along - (t if ang in (0, 270) else -t))
                assert d >= CLIP_W / 2 + CLIP_SLOT + INSERT_D / 2 + 1.0, f"clip at {t} too close to a lid screw"
    assert BODY_H - BAND_H - DRIP_IN + DRIP_H <= BODY_H - INSERT_DEPTH - 1.0, "drip notch runs into the lid inserts"
    assert DRIP_IN >= CLIP_ENG + CLIP_CLR + 0.4, "drip notch runs into the clip ledges"
    open_rays = rain_check(parts)
    assert not open_rays, f"rain reaches an opening: {open_rays[:5]}"
    top_gland = Z0 + OPENING_Z + GLAND_NUT[0] / 2
    assert top_gland <= BODY_H - BAND_H - BAND_OUT + 0.5, "gland hex hits the band chamfer"
    return dm


# ----------------------------------------------------------------------------- output
def build():
    return {"body": body(), "lid": lid(), "deck": deck(), "board clamp": board_clamp(), "shoe": shoe(), "rack plate": rack_plate(),
            "ribbon clamp": ribbon_clamp(), "rear hood": hood(1), "front hood": hood(-1)}


def print_pose(name, p):
    """Each part flat side down at z = 0, as it goes on the build plate."""
    if name in ("lid", "shoe"):
        p = p.rotate((0, 0, 0), (1, 0, 0), 180)
    elif name == "board clamp":   # top face down, slots up, lying along X
        p = p.rotate((0, 0, 0), (1, 0, 0), 180).rotate((0, 0, 0), (0, 0, 1), 90)
    elif name == "rear hood":   # front face down, long side along X
        p = p.rotate((0, 0, 0), (0, 1, 0), 90).rotate((0, 0, 0), (0, 0, 1), 90)
    elif name == "front hood":
        p = p.rotate((0, 0, 0), (0, 1, 0), -90).rotate((0, 0, 0), (0, 0, 1), 90)
    elif name == "ribbon clamp":   # on its side: the end face holds the whole profile (clamp, visor roof, cheek)
        p = p.rotate((0, 0, 0), (0, 1, 0), 90)
    bb = p.val().BoundingBox()
    return p.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


PLATES = {  # one 3MF per build plate; parts in rows along Y, 10 mm apart
    "box_v2_plate1_body": ["body"],
    "box_v2_plate2_lid": ["lid"],
    "box_v2_plate3_deck": ["deck", "board clamp", "ribbon clamp"],
    "box_v2_plate4_rack_plate": ["rack plate"],
    "box_v2_plate5_shoe": ["shoe"],
    "box_v2_plate6_hoods": ["rear hood", "front hood"],
}


def write_plates(out):
    import trimesh
    from plate3mf import BED, export_3mf
    for plate, names in PLATES.items():
        meshes, y = {}, 0.0
        for n in names:
            m = trimesh.load(out / f"box_v2_{n.replace(' ', '_')}.stl")
            m.apply_translation([-m.bounds[0][0], y - m.bounds[0][1], 0])
            y = m.bounds[1][1] + 10.0
            meshes[n.replace(" ", "_")] = m
        wide = max(m.bounds[1][0] for m in meshes.values())
        assert y - 10.0 <= BED - 10 and wide <= BED - 10, f"{plate} does not fit the {BED:g} mm plate"
        export_3mf(meshes, str(out / f"{plate}.3mf"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1] / "print")
    out = ap.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    parts = build()
    check(parts)
    asm = cq.Assembly(name="box_v2")
    colors = {"body": "gray", "lid": "lightgray", "deck": "white", "board clamp": "white", "shoe": "gray", "rack plate": "black", "ribbon clamp": "gray",
              "rear hood": "lightgray", "front hood": "lightgray"}
    for name, p in parts.items():
        asm.add(p, name=name.replace(" ", "_"), color=cq.Color(colors[name]))
    asm.save(str(out / "box_v2.step"))
    for name, p in parts.items():
        cq.exporters.export(print_pose(name, p), str(out / f"box_v2_{name.replace(' ', '_')}.stl"), tolerance=0.05, angularTolerance=0.2)
    write_plates(out)
    bb = parts["body"].val().BoundingBox()
    print(f"box v2: body {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, inside {IN_L:g} x {IN_W:g} x {IN_H:g}")
    print(f"deck top {DECK_Z:.1f} mm above the outside bottom, bank under it; lane {LANE[1] - LANE[0]:.1f} mm wide")
    for name, p in parts.items():
        b = print_pose(name, p).val().BoundingBox()
        print(f"  {name:13s} {b.xlen:6.1f} x {b.ylen:6.1f} x {b.zlen:5.1f}  {p.val().Volume() / 1000:6.1f} cm3")
    print("all checks passed")


if __name__ == "__main__":
    main()
