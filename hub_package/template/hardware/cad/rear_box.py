"""Empty rear-rack enclosure. Dimensions are in millimetres."""

import argparse
from pathlib import Path

import cadquery as cq


def rounded_block(length, width, radius, z, height):
    return (
        cq.Workplane("XY", origin=(0, 0, z))
        .rect(length, width)
        .extrude(height)
        .edges("|Z")
        .fillet(radius)
    )


def build():
    body = rounded_block(220, 124, 10, 0, 65)
    body = body.union(rounded_block(240, 144, 12, 65, 6))
    body = body.cut(rounded_block(214, 118, 7, 3, 70))

    # 3 mm gasket cord sits 0.75 mm proud before the lid bottoms out.
    groove = rounded_block(228, 132, 14, 68.75, 3)
    groove = groove.cut(rounded_block(221, 125, 10.5, 68, 5))
    body = body.cut(groove)
    lid = rounded_block(240, 144, 12, 71, 4)

    # Fasteners pass through the flange beyond the gasket.
    screw_centres = [(x, y) for x in (-95, -48, 0, 48, 95) for y in (-69, 69)]
    screw_centres += [(x, 0) for x in (-117, 117)]
    holes = cq.Workplane("XY", origin=(0, 0, 64)).pushPoints(screw_centres).circle(1.7).extrude(12)
    body = body.cut(holes)
    lid = lid.cut(holes)

    # Four external tabs take straps up to 20 mm wide. The slots are
    # vertical so the straps can loop down around the rack rails.
    for x in (-55, 55):
        for y in (-65, 65):
            tab = rounded_block(30, 14, 2, 0, 6).translate((x, y, 0))
            slot = rounded_block(22, 4, 1.9, -1, 8).translate((x, y + (1 if y > 0 else -1), 0))
            body = body.union(tab.cut(slot))

    # +X faces the rear of the rack. Keep the first 35 mm inside this
    # wall clear for gland locknuts, connectors and cable bends.
    rear_wall = cq.Workplane("YZ", origin=(106, 0, 0))
    glands = rear_wall.pushPoints([(-33, 24), (-11, 24), (11, 24), (33, 24)]).circle(8.1).extrude(5)
    ribbon = rear_wall.center(0, 48).slot2D(24, 5).extrude(5)
    body = body.cut(glands).cut(ribbon)

    return body, lid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "print")
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    body, lid = build()
    for name, part in (("rear_box_body", body), ("rear_box_lid", lid.translate((0, 0, -71)))):
        if len(part.solids().vals()) != 1 or not part.val().isValid():
            raise ValueError(f"{name} must be one valid solid")
        cq.exporters.export(part, str(out / f"{name}.stl"), tolerance=0.05)
    assembly = cq.Assembly(name="rear_box")
    assembly.add(body, name="body")
    assembly.add(lid, name="lid")
    assembly.export(str(out / "rear_box.step"))


if __name__ == "__main__":
    main()
