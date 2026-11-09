"""Write a print plate as a 3MF that Bambu Studio opens, the layout centred on the 256 x 256 mm plate of the P2S.
trimesh's 3MF writer leaves out every build item whose node name starts with "camera" (it takes it for a scene camera),
so a plate of camera_* parts came out with an empty build list and Bambu Studio reported no geometry. The objects keep
their part names; only the build nodes get a prefix."""
import zipfile

import trimesh

BED = 256.0


def export_3mf(parts, path):
    lo = min(m.bounds[0][0] for m in parts.values()), min(m.bounds[0][1] for m in parts.values())
    hi = max(m.bounds[1][0] for m in parts.values()), max(m.bounds[1][1] for m in parts.values())
    shift = [BED / 2 - (lo[0] + hi[0]) / 2, BED / 2 - (lo[1] + hi[1]) / 2, 0.0]
    scene = trimesh.Scene()
    for name, mesh in parts.items():
        m = mesh.copy()
        m.apply_translation(shift)
        scene.add_geometry(m, node_name="part_" + name, geom_name=name)
    scene.export(path)
    model = zipfile.ZipFile(path).read("3D/3dmodel.model")
    assert model.count(b"<item ") == len(parts), f"{path}: not every part is on the build plate"
