"""Meshes for the 3D view in the knowledge editor (python3 hardware/knowledge/kb.py serve).

Run:  python hardware/cad/preview.py [--out hardware/cad/out/preview]
Writes one JSON per model (box_v2, tray, ultrasonic_box, camera_housing, wheel_sensor, rear_box). Each lists its components: a name, whether it is a printed part or a
translucent "ghost" (the real part that sits in it, or a hole), the keys of parameters.json that size it, and its triangles.
Clicking a component in the editor jumps to those parameters; focusing a parameter highlights the component.
"""
import argparse
import json
import os
import pathlib

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS = {p["key"] for p in json.loads(pathlib.Path(HERE, "parameters.json").read_text())["parameters"]}


def mesh(shape, tol=0.12):
    """Triangles of a CadQuery workplane as flat lists: vertices x,y,z,... and indices."""
    v, t = shape.val().tessellate(tol, 0.35)
    return [round(c, 2) for p in v for c in (p.x, p.y, p.z)], [k for tri in t for k in tri]


def comp(cid, label, shape, params, kind="part", visible=True, hint=""):
    v, t = mesh(shape)
    return {"id": cid, "label": label, "kind": kind, "visible": visible, "hint": hint,
            "params": [k for k in params if k in PARAMS], "v": v, "t": t}


def tray():
    import enclosure as e
    e.set_layout(False)
    imu_board = e.place_imu(e.bno085_dummy().rotate((0, 0, 0), (0, 0, 1), 90).translate((0, 0, e.FT)))
    cs = [
        comp("frame", "Tray frame (floor and rim)", e.frame(False), ["W", "L", "FT", "RX", "RY", "WR", "OR", "FIT", "WALL", "NOTCH_X", "NOTCH_Y"],
             hint="The flat frame that sits on the box floor. The corner cut-out sizes only matter for the notched variant."),
        comp("pi", "Raspberry Pi pocket and pedestal", e.pi_pocket(), ["PI_LIFT", "WALL_H_PI", "PI_INSET", "PI_SIDE_INSET", "OVERLAP", "CZ", "PI_CORNER"]),
        comp("pi_case", "Pi 5 in its case", e.blk(*e.PI, e.PI_H, e.pcx, e.pcy, e.FT + e.PI_LIFT), ["PI_X", "PI_Y", "PI_H"], kind="ghost",
             hint="Not printed: the Pi in its case, as measured."),
        comp("holder", "Breadboard holder", e.holder(), ["BB_GAP", "EWT", "EWD", "EWH"]),
        comp("breadboard", "Breadboard (on its edge)", e.blk(e.BBT, e.BBL, e.BBH, e.xb - e.BBT / 2, e.hcy, e.FT), ["BBL", "BBT", "BBH"], kind="ghost"),
        comp("imu", "IMU pocket", e.place_imu(e.imu_module()), ["IMX", "WALL_H_IMU", "OPENW", "EAR_R", "EAR_W", "EAR_X", "PIN_HOLE"]),
        comp("imu_board", "IMU board (BNO085)", imu_board, ["IMU_X", "IMU_Y"], kind="ghost"),
        comp("imu_lid", "IMU hinged lid", e.place_imu(e.imu_lid()), ["LID_T", "LID_CLR", "BARREL_HW", "ARM_T", "ARM_HW", "BUMP", "BARB"]),
        comp("gps", "GPS pocket", e.gps_walls(), ["GWALL_H", "GCABLE_W"]),
        comp("us_pocket", "Ultrasonic shell pocket", e.shell_pocket(), ["US_TRAY", "US_T_WALL", "US_T_H", "US_WIRE_D"], hint="Pocket for one ultrasonic shell, upside down so the probe cable hole faces the box lid. Standard tray only."),
        comp("us_shell", "Ultrasonic shell (closed)", e.shell_geom()[6], [], kind="ghost", hint="Not printed: the shell with its lid, hole facing up."),
        comp("gps_rx", "GPS receiver", e.blk(*e.GPS, e.GCX, e.gcy, e.FT), ["GPS_X", "GPS_Y", "GPS_H"], kind="ghost"),
        comp("trunk", "Cable channel", e.trunk_solid(), ["TX", "CH_W", "CH_H", "CH_WALL", "CH_FLOOR"]),
        comp("cable_lid", "Cable channel lid", e.cable_lid(), ["CH_LID_T", "CH_LID_OVER", "CH_TAB_H"]),
    ]
    return {"model": "tray", "title": "Tray (standard)", "components": cs}


def ultrasonic_box():
    import ultrasonic_box as u
    ties = None
    for ty in u.TIES:
        b = u.blk(2 * u.XO, u.TIE_W, u.TIE_T, u.CXM, ty, 2.0)
        ties = b if ties is None else ties.union(b)
    cs = [
        comp("body", "Box", u.build_housing(), ["US_FL", "US_WALL", "US_STANDOFF", "US_DUP_LEN", "US_PLUG_OVER"]),
        comp("lid", "Lid", u.build_lid(), ["US_LID_T"], visible=False, hint="Hidden by default so you can see inside. Tick it in the part list to show it."),
        comp("board", "Control board (AJ-SR04M)", u.board_dummy(), ["US_BX", "US_BY", "US_BT", "US_HDX", "US_HDY", "US_HD", "US_BACK_H", "US_TOP_H"], kind="ghost",
             hint="Not printed: the board with its probe plug and header (sizes estimated from photos)."),
        comp("probe_hole", "Probe cable hole (floor)", u.cyl(u.PROBE_D / 2, -0.5, u.FL + 0.5, u.XH, u.YH), ["US_PROBE_D", "US_CENTER"], kind="ghost",
             hint="The hole in the floor, shown as the solid that is cut away."),
        comp("dent", "Plug dent (floor)", u.blk(u.DENT_W, u.DENT_Y1 - u.DENT_Y0, u.DENT_D, 0.0, (u.DENT_Y0 + u.DENT_Y1) / 2, u.FL - u.DENT_D), ["US_STANDOFF", "US_BACK_H"], kind="ghost"),
        comp("wire_notch", "Wire notch (+X wall)", u.blk(u.RIM + 2.0, u.WIRE_D, u.H - u.NOTCH_Z + 1.0, u.CXM + u.CX / 2 + u.RIM / 2, u.YB, u.NOTCH_Z), ["US_WIRE_D"], kind="ghost",
             hint="Open from the top, next to the header; the lid closes it."),
        comp("ties", "Zip-tie tunnels", ties, ["US_TIE_W", "US_TIE_T"], kind="ghost"),
    ]
    return {"model": "ultrasonic_box", "title": "Ultrasonic box", "components": cs, "general": {"label": "Print plate", "params": ["US_COUNT"]}}


def camera_housing():
    import camera_housing as c
    cs = [
        comp("housing", "Housing", c.build_housing(), ["C_CAV_GAP", "C_RIB_ROOM", "C_BACK_ROOM", "C_LG", "C_BLOCK_GAP", "C_WALL", "C_CORNER",
                                                       "C_INS_D", "C_INS_DEEP", "C_POST_R", "C_FL", "C_FT", "C_TAPER"],
             hint="Front wall, depth and clamp block are worked out from the camera and the rack tube."),
        comp("lid", "Lid", c.build_lid(), ["C_LID_T", "C_PEG_D", "C_PEG_GAP", "C_LIP_H", "C_LIP_T", "C_FL"], visible=False,
             hint="Hidden by default so you can see inside. Goes straight on: four pegs press the board, a lip keeps it square."),
        comp("locks", "Lock bars (2)", c.build_bar(1).union(c.build_bar(-1)), ["C_BAR_T", "C_HEAD", "C_SL_GAP", "C_SL_PLAY", "C_TAPER"],
             visible=False, hint="Slide down from the top over the rail and the lid flange on each side; the tapered rail pulls the lid tight. Pull up by the heads to open."),
        comp("cap", "Rack clamp cap", c.build_cap(), ["C_CAP_GAP", "C_CAP_L", "C_CAP_TOP", "C_HEAD_D", "C_UNDER_HEAD", "C_SCREW_EDGE"],
             hint="Two M3 screws pull it onto the rack tube, into inserts in the block on top of the housing."),
        comp("tube", "Rack tube", c.tube_dummy(), ["C_RACK_D", "C_RACK_PAD", "C_TUBE_UP"], kind="ghost",
             hint="Not printed: the back end of the rear rack, running sideways (diameter is an ESTIMATE)."),
        comp("board", "Camera Module 3 Wide", c.camera_dummy(), ["C_CAM_W", "C_CAM_H", "C_CAM_T", "C_HOLE_DX", "C_HOLE_DZ", "C_HOLE_Z0", "C_HOLE_D",
                                                                  "C_PAD_D", "C_LENS_X", "C_LENS_Z0", "C_LENS_W", "C_LENS_H", "C_LENS_TOP",
                                                                  "C_NOSE_D", "C_DEPTH_ALL", "C_CONN_W", "C_CONN_H", "C_RIB_W", "C_FOV_D", "C_GLASS_D"],
             kind="ghost", hint="Not printed: board, lens and connector, sized from the official Raspberry Pi drawing."),
        comp("window", "Window plate", c.window_dummy(), ["C_WIN", "C_WIN_T", "C_WIN_RECESS"], kind="ghost",
             hint="Clear plastic plate bonded into the recess in the front."),
        comp("groove", "Gasket groove", c.groove_ring(), ["C_GROOVE_W", "C_GROOVE_D", "C_GROOVE_R", "C_CORD"], kind="ghost",
             hint="The groove for the foam cord, shown as the solid that is cut away."),
        comp("slot", "Ribbon slot", c.ribbon_slot(), ["C_SLOT_W", "C_SLOT_T"], kind="ghost",
             hint="Straight down through the floor, under the connector: the ribbon needs no bend."),
        comp("ribbon", "Ribbon", c.ribbon_dummy(), ["C_RIB_W"], kind="ghost", hint="Not printed: the flat camera cable."),
    ]
    return {"model": "camera_housing", "title": "Camera housing", "components": cs}


def wheel_sensor():
    import wheel_sensor as w
    cs = [
        comp("clamp", "Clamp (also printed alone: fit test)", w.build_clamp(), ["WS_TUBE_H", "WS_TUBE_W", "WS_TUBE_R", "WS_PAD", "WS_BODY_H", "WS_BACK", "WS_SIDE",
                                                                                "WS_TIE_W", "WS_TIE_T"],
             hint="The C that holds the stay; its opening is the stay size (depth = the flat face, width, corner radius) plus the pad. wheel_sensor_fit.stl / .3mf is this clamp alone, built from the same numbers: print it to try on the stay before printing the whole bracket."),
        comp("holder", "Arm and sensor holder", w.build().cut(w.build_clamp()), ["WS_CHIP_GAP", "WS_WALL", "WS_BODY_H", "WS_CABLE_W"]),
        comp("cable", "Cable slot (pocket floor)", w.cable_slot(), ["WS_CABLE_W"], kind="ghost",
             hint="A hole, not a part: the wires leave the board's header through the middle of the pocket floor. Fill with silicone after routing."),
        comp("stay", "Seatstay", w.tube_dummy(), ["WS_TUBE_W", "WS_TUBE_H", "WS_TUBE_R"], kind="ghost",
             hint="Not printed: the left rear seatstay, D-shaped (flat towards the wheel), snapped into the clamp from the open side."),
        comp("board", "Hall board (KY-003)", w.board_dummy(), ["WS_BOARD_Y", "WS_BOARD_Z", "WS_BOARD_T", "WS_COMP_H"], kind="ghost"),
        comp("magnet", "Spoke magnet", w.magnet_dummy(), ["WS_SPOKE_GAP"], kind="ghost",
             hint="Not printed: only its near face matters, set by the stay-to-magnet distance."),
    ]
    return {"model": "wheel_sensor", "title": "Wheel sensor", "components": cs}


def box_v2():
    import box_v2 as b
    import cadquery as cq

    parts = b.build()
    dm = b.dummies()
    ghosts = cq.Workplane(obj=cq.Compound.makeCompound([d.val() for d in dm.values()]))
    info = [
        ("body", "Box body", True, ("Walls, floor and the top band with the lid inserts, foam-cord groove, snap clip ledges and the drip notch. "
                                    "Deck columns, power bank cradle and IMU pocket inside; the four ultrasonic boards stand on the rear wall.")),
        ("lid", "Lid", False, "Hidden by default so you can see inside. Ten snap clips on the skirt hold it shut; the 14 M3 screws add the force."),
        ("deck", "Deck", True, "Removable plate on six columns: Pi, breadboard, GPS, spare bay, cable lane. The power bank lies under it."),
        ("board clamp", "Board clamp bar", True, "Holds the top edges of the four ultrasonic boards; two M3 into the end posts."),
        ("ribbon clamp", "Ribbon clamp and visor", True, "Presses foam onto the camera ribbon where it leaves the +Y wall; its roof reaches back to the wall."),
        ("rear hood", "Rear rain hood", True, "Over the four probe glands; foam strip between its roof and cheeks and the wall."),
        ("front hood", "Front rain hood", True, "Over the charge port, button and wheel sensor gland."),
        ("shoe", "Shoe", True, "Screws under the box and slides onto the rack plate's dovetail rails."),
        ("rack plate", "Rack plate", True, "Strapped to the rack with hose clamps or UV ties; one M3 locks the shoe."),
    ]
    cs = [comp(k.replace(" ", "_"), label, parts[k], [], visible=vis, hint=hint) for k, label, vis, hint in info]
    cs.append(comp("electronics", "Electronics, glands and ports", ghosts, [], kind="ghost",
                   hint="Not printed: Pi, breadboard, GPS, IMU, power bank, ultrasonic boards and the gland bodies, as sized in box_v2.py."))
    return {"model": "box_v2", "title": "Main box v2", "components": cs}


def rear_box():
    from enclosure import build_tray
    from rear_box import build

    body, lid = build()
    fitted_tray = build_tray(False).rotate((0, 0, 0), (0, 0, 1), -90).translate((-17, 0, 3))
    assert fitted_tray.intersect(body).val().Volume() < 0.001
    return {"model": "rear_box", "title": "Main rear-rack box", "components": [
        comp("body", "Box body", body, [],
             hint="Rear wall: four Ø16.2 mm M16 gland holes and one 24 × 5 mm camera ribbon slot. Position the standard Bike Plate tray 17 mm toward the front to leave 37 mm behind it for cables."),
        comp("lid", "Gasketed lid", lid, [],
             hint="Hide the lid to inspect the cavity. Fit 3 mm gasket cord in the body groove."),
        comp("bike_tray", "Bike Plate 1 tray (fit reference)", fitted_tray, [], kind="ghost", visible=False),
    ]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "out", "preview"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for build in (box_v2, tray, ultrasonic_box, camera_housing, wheel_sensor, rear_box):
        m = build()
        with open(os.path.join(a.out, m["model"] + ".json"), "w") as f:
            json.dump(m, f, separators=(",", ":"))
        n = sum(len(c["t"]) // 3 for c in m["components"])
        print(f"{m['model']}: {len(m['components'])} components, {n} triangles")


if __name__ == "__main__":
    main()
