import argparse
import os
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from PIL import Image, ImageDraw

def read_3mf_part_grays(input_path):
    """Reads exact part names and sRGB hex colors directly from Onshape's 3MF XML."""
    part_colors = {}
    try:
        with zipfile.ZipFile(input_path, 'r') as z:
            model_files = [f for f in z.namelist() if f.endswith('.model')]
            for mf in model_files:
                xml_data = z.read(mf)
                root = ET.fromstring(xml_data)
                ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
                
                # Map basematerials group_id -> list of hex colors
                materials = {}
                for bm in root.findall('.//m:basematerials', ns):
                    bm_id = bm.attrib.get('id')
                    colors = []
                    for base in bm.findall('m:base', ns):
                        hex_col = base.attrib.get('displaycolor', '#FFFFFF').lstrip('#')
                        r = int(hex_col[0:2], 16)
                        g = int(hex_col[2:4], 16)
                        b = int(hex_col[4:6], 16)
                        gray = int(round(0.299 * r + 0.587 * g + 0.114 * b))
                        colors.append(max(0, min(255, gray)))
                    materials[bm_id] = colors

                # Map object name -> grayscale value
                for obj in root.findall('.//m:object', ns):
                    name = obj.attrib.get('name', '')
                    pid = obj.attrib.get('pid')
                    pindex = obj.attrib.get('pindex')
                    if pid in materials and pindex is not None:
                        idx = int(pindex)
                        if idx < len(materials[pid]):
                            part_colors[name] = materials[pid][idx]
    except Exception as e:
        print(f"[WARN] Could not parse XML materials directly: {e}")
    return part_colors

def slice_3mf(input_path, out_dir, layer_mm=0.05, scale=1000.0, part_grays=None, bed_x_mm=68.0, bed_y_mm=38.0, pixel_mm=0.035):
    os.makedirs(out_dir, exist_ok=True)
    xml_grays = read_3mf_part_grays(input_path)
    loaded = trimesh.load(input_path, force='scene')
    
    parts = []
    idx_part = 0
    for name, geom in loaded.geometry.items():
        if isinstance(geom, trimesh.Trimesh) and len(geom.faces) > 0:
            geom = geom.copy()
            nodes = loaded.graph.geometry_nodes.get(name, [])
            if nodes:
                matrix, _ = loaded.graph.get(nodes[0])
                geom.apply_transform(matrix)
            
            # Scale coordinates (e.g., 1000x to convert Onshape 3MF meters -> mm)
            geom.apply_scale(scale)

            # Determine gray value: manual override -> XML color -> default 255
            if part_grays and idx_part < len(part_grays):
                gray_val = max(0, min(255, int(part_grays[idx_part])))
            elif name in xml_grays:
                gray_val = xml_grays[name]
            else:
                gray_val = 255
                
            parts.append((name, geom, gray_val))
            print(f"[PART {idx_part + 1}] '{name}': grayscale value = {gray_val}/255 ({round(gray_val/255*100)}%)")
            idx_part += 1

    if not parts:
        raise ValueError("No valid 3D meshes found in the 3MF file.")

    all_bounds = np.array([p[1].bounds for p in parts])
    min_xyz = all_bounds[:, 0, :].min(axis=0)
    max_xyz = all_bounds[:, 1, :].max(axis=0)

    z_min, z_max = min_xyz[2], max_xyz[2]
    center_x = (min_xyz[0] + max_xyz[0]) / 2.0
    center_y = (min_xyz[1] + max_xyz[1]) / 2.0

    img_w = int(round(bed_x_mm / pixel_mm))
    img_h = int(round(bed_y_mm / pixel_mm))
    bed_center_px = (img_w / 2.0, img_h / 2.0)

    z_heights = np.arange(z_min + (layer_mm / 2.0), z_max, layer_mm)
    print(f"[INFO] Size: {max_xyz[0]-min_xyz[0]:.2f} x {max_xyz[1]-min_xyz[1]:.2f} x {z_max-z_min:.2f} mm | Generating {len(z_heights)} layers ({img_w}x{img_h} px)...")

    for idx, z in enumerate(z_heights, start=1):
        layer_canvas = np.zeros((img_h, img_w), dtype=np.uint8)

        for name, mesh, gray_val in parts:
            if z < mesh.bounds[0][2] or z > mesh.bounds[1][2]:
                continue

            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if section is None:
                continue

            slice_2d, to_3d = section.to_planar()
            part_mask = Image.new("L", (img_w, img_h), 0)
            draw = ImageDraw.Draw(part_mask)

            for poly in slice_2d.polygons_full:
                ext_2d = np.column_stack([poly.exterior.coords.xy[0], poly.exterior.coords.xy[1], np.zeros(len(poly.exterior.coords))])
                ext_world = trimesh.transform_points(ext_2d, to_3d)
                
                px_x = bed_center_px[0] + (ext_world[:, 0] - center_x) / pixel_mm
                px_y = bed_center_px[1] - (ext_world[:, 1] - center_y) / pixel_mm
                coords = list(zip(px_x, px_y))
                if len(coords) >= 3:
                    draw.polygon(coords, fill=gray_val)

                for interior in poly.interiors:
                    int_2d = np.column_stack([interior.coords.xy[0], interior.coords.xy[1], np.zeros(len(interior.coords))])
                    int_world = trimesh.transform_points(int_2d, to_3d)
                    hx = bed_center_px[0] + (int_world[:, 0] - center_x) / pixel_mm
                    hy = bed_center_px[1] - (int_world[:, 1] - center_y) / pixel_mm
                    h_coords = list(zip(hx, hy))
                    if len(h_coords) >= 3:
                        draw.polygon(h_coords, fill=0)

            layer_canvas = np.maximum(layer_canvas, np.array(part_mask))

        out_file = os.path.join(out_dir, f"layer_{idx:04d}.png")
        Image.fromarray(layer_canvas, mode="L").save(out_file)

    print(f"✅ Done! Wrote {len(z_heights)} grayscale layers to {out_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slice a multi-part 3MF file into grayscale PNGs for LumenX Gen-3.")
    parser.add_argument("--input", required=True, help="Path to your .3mf file")
    parser.add_argument("--layer-mm", type=float, default=0.05, help="Layer thickness in mm (default: 0.05)")
    parser.add_argument("--scale", type=float, default=1000.0, help="Scale multiplier (default: 1000.0 for Onshape 3MF meters->mm)")
    parser.add_argument("--part-grays", nargs="+", type=int, help="Optional: override 0-255 gray values for Part 1, Part 2, etc.")
    parser.add_argument("--out", required=True, help="Output folder for PNG layers")
    args = parser.parse_args()

    slice_3mf(args.input, args.out, layer_mm=args.layer_mm, scale=args.scale, part_grays=args.part_grays)
