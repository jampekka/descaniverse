from . import scaniverse_pb2
from google.protobuf.json_format import MessageToDict
from pathlib import Path
import sys
import json
from typing import Union, TextIO, Optional
import os.path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
import re
import unicodedata
import zlib
import liblzfse as lzfse


def decode_depth_dmp(depth_buf):
    """Decompress a Scaniverse ``.dmp`` depth file to raw float16 bytes.

    Two on-disk formats are supported:

    * Legacy: a bare LZFSE stream.
    * Newer: a 12-byte header -- ``b'DMP0'`` magic, uint32 little-endian
      file size, uint16 width, uint16 height -- followed by a
      zlib-compressed float16 payload.

    The format is detected from the leading magic bytes.
    """
    if depth_buf[:4] == b'DMP0':
        return zlib.decompress(depth_buf[12:])
    return lzfse.decompress(depth_buf)


def message_to_dict(msg):
    return MessageToDict(msg, including_default_value_fields=True)

class ScaniverseRawData:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.scan = scaniverse_pb2.Scan.FromString(
                open(directory / "scan.pb", 'rb').read()
                )
        
        self.frames = scaniverse_pb2.Frames.FromString(
open(directory / "frames.pb", 'rb').read()
                )

    def as_dict(self):
        return {
            'directory': str(self.directory),
            'scan': MessageToDict(self.scan),
            'frames': MessageToDict(self.frames)
                }

class FakePath:
    def __init__(self, file, name):
        self.file = file
        self.name = name

    def __str__(self):
        return self.name

    def open(self, *args, **kwargs):
        return self.file


def _sanitize_name(name):
    """Turn a scan name into a filesystem-safe ASCII slug."""
    ascii_name = (
        unicodedata.normalize("NFKD", name or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-")
    return slug or "unnamed"


def _with_scan_name(path, scan):
    """Append a scan's sanitized name to a file or directory path."""
    suffix = _sanitize_name(scan.name)
    if path.suffix:
        return path.with_name(f"{path.stem}_{suffix}{path.suffix}")
    return path.with_name(f"{path.name}_{suffix}")


def _with_timestamp_prefix(path, scan):
    """Prefix a file or directory name with the scan's capture timestamp.

    The timestamp is formatted YYYYMMDD-HHMMSS from the scan's createdAt.
    """
    import datetime
    stamp = datetime.datetime.fromtimestamp(scan.createdAt).strftime(
        "%Y%m%d-%H%M%S")
    return path.with_name(f"{stamp}_{path.name}")


def scaniverse_to_json(scaniverse_dir: Path, output: Path=FakePath(sys.stdout, "STDOUT"),
                       append_scan_name: bool=False,
                       prefix_timestamp: bool=False):
    """Converts Scaniverse metadata as-is to JSON"""
    scan = ScaniverseRawData(scaniverse_dir)
    if append_scan_name and isinstance(output, Path):
        output = _with_scan_name(output, scan.scan)
    if prefix_timestamp and isinstance(output, Path):
        output = _with_timestamp_prefix(output, scan.scan)
    if output is None:
        output = sys.stdout
    else:
        output = output.open('w')
    json.dump(scan.as_dict(), output, indent=2)
    output.write('\n')

def scaniverse_to_nerfstudio(scaniverse_dir: Path, output_dir: Path,
                             depth_images: bool=True, copy_images: bool=True,
                             max_frames: Optional[int]=None,
                             append_scan_name: bool=False,
                             prefix_timestamp: bool=False):
    """Converts a Scaniverse scan to nerfstudio format"""
    # TODO: Currently reads only large frames
    scan = ScaniverseRawData(scaniverse_dir)
    if append_scan_name:
        output_dir = _with_scan_name(output_dir, scan.scan)
    if prefix_timestamp:
        output_dir = _with_timestamp_prefix(output_dir, scan.scan)
    
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir/"transforms.json"
    output_image_dir = output_dir/"images_large"
    output_depth_dir = output_dir/"depth"
    
    input_image_dir = scaniverse_dir/"imgl"
    input_depth_dir = scaniverse_dir/"depth"

    if copy_images: output_image_dir.mkdir(exist_ok=True)
    if depth_images: output_depth_dir.mkdir(exist_ok=True)
    
    conf = scan.scan.configuration
    w_large, h_large = conf.largeImageSize.width, conf.largeImageSize.height
    w_small, h_small = conf.smallImageSize.width, conf.smallImageSize.height
    w_depth, h_depth = conf.depthSize.width, conf.depthSize.height
    
    small_to_large = w_large/w_small
    assert small_to_large == h_large/h_small

    transforms = dict(
        camera_model="OPENCV",
        w=w_large,
        h=h_large,
        frames=[],
        scaniverse_scan=MessageToDict(scan.scan),
    )
    frames = transforms['frames']
    
    for frame in scan.frames.frames:
        if not frame.isLargeImage:
            continue

        file_base = f"{frame.id:>05d}"
        
        camera = frame.camera
        focal_length = camera.f*small_to_large

        quat = np.array(frame.transform.rotation)
        rotation = Rotation.from_quat(quat).as_matrix()
        translation = np.array(frame.transform.translation).reshape(3, 1)
        
        # Scaniverse is in same coordinate system as COLMAP, so copypasting
        # the conversion from here: https://github.com/nerfstudio-project/nerfstudio/blob/a484d255b4f71c55915afcfc52d90ec88963779f/nerfstudio/process_data/colmap_utils.py#L426C7-L428
        # Note that unlike COLMAP, Scaniverse is already in the camera-to-world
        # system, so it doesn't have to be inverted.
        c2w = np.concatenate([rotation, translation], 1)
        c2w = np.concatenate([c2w, np.array([[0, 0, 0, 1]])], 0)
        c2w[0:3, 1:3] *= -1
        c2w = c2w[np.array([1, 0, 2, 3]), :]
        c2w[2, :] *= -1

        data = dict(
            cx=camera.px*small_to_large,
            cy=camera.py*small_to_large,
            fl_x=focal_length,
            fl_y=focal_length,
            transform_matrix=c2w.tolist(),
        )

        input_image_path = input_image_dir/f"{file_base}.jpg"
        if copy_images:
            dst = output_image_dir/input_image_path.name
            shutil.copyfile(input_image_path, dst)
            data['file_path'] = str(dst.relative_to(output_dir))
        else:
            # TODO: Uses absolute
            data['file_path'] = os.path.relpath(input_image_path, output_dir)
        
        if depth_images:
            from PIL import Image
            input_depth_path = input_depth_dir/f"{file_base}.dmp"
            depth_buf = open(input_depth_path, 'br').read()
            depth_buf = decode_depth_dmp(depth_buf)
            depth_data = np.frombuffer(depth_buf, dtype=np.float16)
            try:
                depth_data = depth_data.reshape(h_depth, w_depth)
            except ValueError as e:
                print(f"Skipping frame {frame.id}; invalid depth data: " + str(e), file=sys.stderr)
                continue
            # Convert depth from meters to millimeters:
            # https://docs.nerf.studio/quickstart/data_conventions.html#depth-images
            # Depth zero means missing in both Scaniverse and in nerfstudio
            depth_uint16 = (depth_data*1000).astype(np.uint16)

            dst = output_depth_dir/f"{file_base}.png"
            Image.fromarray(depth_uint16).save(dst)
            data["depth_file_path"] = str(dst.relative_to(output_dir))

        data['scaniverse_frame'] = MessageToDict(frame)
        frames.append(data)
        # TODO: Do uniformish sampling instead
        if max_frames and len(frames) >= max_frames:
            break
    
    json.dump(transforms, open(output_file, 'w'), indent=2)
    #small_to_big_w = scan.
    from pprint import pprint
    #pprint(transforms, sort_dicts=False)
    #transforms = {
    #
    #        }


def _voxel_downsample(points, colors, voxel_size):
    """Keep one representative point (and its color) per voxel cell."""
    cells = np.floor(points / voxel_size).astype(np.int64)
    _, keep = np.unique(cells, axis=0, return_index=True)
    return points[keep], colors[keep]


def _write_ply(path, chunks):
    """Stream (points, colors) chunks to a binary little-endian PLY file.

    `chunks` is any iterable of (points Nx3, colors Nx3 uint8) arrays. The
    vertex count is patched into the header once streaming is done, so the
    whole cloud is never held in memory at once.
    """
    record = np.dtype([
        ("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
        ("red", "u1"), ("green", "u1"), ("blue", "u1"),
    ])
    total = 0
    with open(path, "wb") as fh:
        fh.write(b"ply\nformat binary_little_endian 1.0\nelement vertex ")
        count_offset = fh.tell()
        fh.write(b" " * 24 + b"\n")  # placeholder, patched after streaming
        fh.write(
            b"property float x\nproperty float y\nproperty float z\n"
            b"property uchar red\nproperty uchar green\nproperty uchar blue\n"
            b"end_header\n"
        )
        for points, colors in chunks:
            points = np.asarray(points)
            colors = np.asarray(colors)
            if len(points) == 0:
                continue
            vertex = np.empty(len(points), dtype=record)
            vertex["x"], vertex["y"], vertex["z"] = points.T
            vertex["red"], vertex["green"], vertex["blue"] = colors.T
            fh.write(vertex.tobytes())
            total += len(points)
        fh.seek(count_offset)
        fh.write(str(total).encode("ascii"))
    return total


def _utm_epsg(lat, lon):
    """EPSG code of the WGS84 / UTM zone containing (lat, lon)."""
    zone = int((lon + 180) / 6) % 60 + 1
    return (32600 if lat >= 0 else 32700) + zone


def _write_las(path, chunks, lat0, lon0, elev0, created=None):
    """Write a georeferenced LAS file in the local UTM zone.

    `chunks` yields (points, colors), where points are ENU meters about
    (lat0, lon0, elev0). They are shifted into the UTM zone covering the
    anchor and written with the matching CRS, so the file lands correctly
    in QGIS, Cesium and other GIS tools. `created`, if given, is a Unix
    timestamp written to the LAS header's creation-date field.
    """
    try:
        import laspy
        from pyproj import CRS, Transformer
    except ImportError as e:
        raise RuntimeError(
            "LAS output needs extra packages: pip install laspy pyproj"
        ) from e

    epsg = _utm_epsg(lat0, lon0)
    crs = CRS.from_epsg(epsg)
    east0, north0 = Transformer.from_crs(
        CRS.from_epsg(4326), crs, always_xy=True).transform(lon0, lat0)

    points, colors = [], []
    for chunk_points, chunk_colors in chunks:
        if len(chunk_points):
            points.append(np.asarray(chunk_points))
            colors.append(np.asarray(chunk_colors))
    if not points:
        return 0
    points = np.concatenate(points)
    colors = np.concatenate(colors)

    header = laspy.LasHeader(version="1.4", point_format=7)
    header.add_crs(crs)
    if created is not None:
        import datetime
        header.creation_date = datetime.date.fromtimestamp(created)
    header.offsets = [east0, north0, elev0]
    header.scales = [0.001, 0.001, 0.001]
    las = laspy.LasData(header)
    las.x = points[:, 0].astype(np.float64) + east0
    las.y = points[:, 1].astype(np.float64) + north0
    las.z = points[:, 2].astype(np.float64) + elev0
    # LAS stores 16-bit color; 257 = 65535 / 255 maps 8-bit cleanly.
    las.red = colors[:, 0].astype(np.uint16) * 257
    las.green = colors[:, 1].astype(np.uint16) * 257
    las.blue = colors[:, 2].astype(np.uint16) * 257
    las.write(str(path))
    return len(points)


# Maps ARKit's Y-up coordinates to Z-up: out = points @ _YUP_TO_ZUP.T.
_YUP_TO_ZUP = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)


def _gps_to_enu(locations, lat0, lon0, elev0):
    """Convert GPS fixes to local East-North-Up meters about a reference.

    Returns an (N, 4) array of (timestamp, east, north, up). Uses an
    equirectangular approximation, accurate to well below GPS noise over
    the small extent of a single scan.
    """
    earth_r = 6378137.0  # WGS84 equatorial radius, meters
    lat0r, lon0r = np.radians(lat0), np.radians(lon0)
    rows = []
    for loc in locations:
        east = earth_r * np.cos(lat0r) * (np.radians(loc.longitude) - lon0r)
        north = earth_r * (np.radians(loc.latitude) - lat0r)
        rows.append((loc.timestamp, east, north, loc.elevationMeters - elev0))
    return np.array(rows, dtype=np.float64)


def _georeference_transform(scan):
    """Fit a transform mapping the scan into a local East-North-Up frame.

    Uses the recorded GPS track: a horizontal rotation + translation
    (Kabsch, scale fixed at 1 since both spaces are metric) and a vertical
    offset are fitted between the camera trajectory and the GPS fixes,
    sampled at matching timestamps.

    Returns (M, t, info), where ``out = points @ M.T + t`` maps the native
    Y-up cloud into the ENU frame and info carries reporting metadata.
    """
    fixes = list(scan.frames.locations)
    if len(fixes) < 2:
        raise RuntimeError("Scan has fewer than 2 GPS fixes; cannot georeference")

    ref = scan.scan.location
    lat0, lon0, elev0 = ref.latitude, ref.longitude, ref.elevationMeters
    enu = _gps_to_enu(fixes, lat0, lon0, elev0)

    frames = scan.frames.frames
    cam_t = np.array([f.timestamp for f in frames], dtype=np.float64)
    cam_p = np.array([list(f.transform.translation) for f in frames],
                     dtype=np.float64) @ _YUP_TO_ZUP.T
    order = np.argsort(cam_t)
    cam_t, cam_p = cam_t[order], cam_p[order]

    enu = enu[(enu[:, 0] >= cam_t[0]) & (enu[:, 0] <= cam_t[-1])]
    if len(enu) < 2:
        raise RuntimeError("GPS fixes do not overlap the frame timestamps")
    local = np.stack([np.interp(enu[:, 0], cam_t, cam_p[:, i])
                      for i in range(3)], axis=1)

    src, dst = local[:, :2], enu[:, 1:3]
    u, _, vt = np.linalg.svd((src - src.mean(0)).T @ (dst - dst.mean(0)))
    flip = np.sign(np.linalg.det(vt.T @ u.T))
    rot = vt.T @ np.diag([1.0, flip]) @ u.T
    trans = dst.mean(0) - rot @ src.mean(0)
    up_offset = enu[:, 3].mean() - local[:, 2].mean()
    rms = float(np.sqrt(((src @ rot.T + trans - dst) ** 2).sum(1).mean()))

    horizontal = np.eye(3)
    horizontal[:2, :2] = rot
    M = horizontal @ _YUP_TO_ZUP
    t = np.array([trans[0], trans[1], up_offset])
    info = dict(lat0=lat0, lon0=lon0, elev0=elev0, n_fixes=len(enu), rms=rms)
    return M, t, info


def _output_transform(scan, z_up, georeference):
    """Return (M, t, info): out = points @ M.T + t for the chosen frame.

    info is None unless georeferencing, in which case it carries the
    anchor location and fit quality for reporting.
    """
    if georeference:
        return _georeference_transform(scan)
    if z_up:
        return _YUP_TO_ZUP, np.zeros(3), None
    return np.eye(3), np.zeros(3), None


def scaniverse_to_pointcloud(scaniverse_dir: Path, output: Path,
                             voxel_size: float = 0.02,
                             max_frames: int = 2000,
                             append_scan_name: bool = False,
                             prefix_timestamp: bool = False,
                             z_up: bool = False,
                             georeference: bool = False):
    """Converts a Scaniverse scan to a colored point cloud

    Each depth map is back-projected to 3D using its per-frame camera
    intrinsics and pose, colored from the matching small image and merged
    into world space. The result is a binary PLY that opens directly in
    CloudCompare, MeshLab or Blender.

    :param scaniverse_dir: A Scaniverse scan directory (scan.pb, frames.pb,
        depth/, img/).
    :param output: Destination file. A .ply extension writes a binary PLY;
        a .las extension writes a georeferenced LAS in the local UTM zone
        (needs the optional laspy and pyproj packages; implies
        georeferencing).
    :param voxel_size: Voxel-downsampling cell size in meters; smaller is
        denser. Use 0 to keep every point (no downsampling).
    :param max_frames: Approximate number of frames to use, sampled at a
        uniform stride across the scan. Use 0 to use every frame.
    :param append_scan_name: Append the scan's sanitized name to the output
        filename (e.g. cloud.ply -> cloud_My-Scan.ply).
    :param prefix_timestamp: Prefix the output filename with the scan's
        capture timestamp, formatted YYYYMMDD-HHMMSS.
    :param z_up: Rotate the output from Scaniverse's native Y-up frame
        (ARKit is gravity-aligned with Y up) to a Z-up frame, as expected
        by CloudCompare and Blender.
    :param georeference: Place the cloud in a local East-North-Up frame
        anchored at the scan's GPS location, fitted from the recorded GPS
        track. Implies Z-up. Accuracy is limited by consumer GPS (the
        horizontal fit RMS, a few meters, is printed).
    """
    from PIL import Image

    scan = ScaniverseRawData(scaniverse_dir)
    if append_scan_name:
        output = _with_scan_name(output, scan.scan)
    if prefix_timestamp:
        output = _with_timestamp_prefix(output, scan.scan)
    frames = list(scan.frames.frames)
    stride = max(1, len(frames) // max_frames) if max_frames else 1
    sampled = frames[::stride]

    want_las = output.suffix.lower() == ".las"
    if want_las and not georeference:
        georeference = True
        print("LAS output: enabling georeferencing (LAS needs a CRS)")
    transform, offset, geo = _output_transform(scan, z_up, georeference)
    transform = transform.astype(np.float32)
    offset = offset.astype(np.float32)

    def frame_chunks():
        """Yield (points, colors) for each used frame, in output coords."""
        total = len(sampled)
        for i, frame in enumerate(sampled):
            if i % 50 == 0:
                print(f"\r  frame {i}/{total} ({100 * i / total:.0f}%)",
                      end="", file=sys.stderr, flush=True)
            base = f"{frame.id:>05d}"
            depth_path = scaniverse_dir / "depth" / f"{base}.dmp"
            image_path = scaniverse_dir / "img" / f"{base}.jpg"
            if not depth_path.exists() or not image_path.exists():
                continue

            camera = frame.camera
            w, h = int(camera.width), int(camera.height)
            depth = np.frombuffer(
                decode_depth_dmp(depth_path.read_bytes()), dtype=np.float16,
            ).astype(np.float32)
            if depth.size != w * h:
                print(f"Skipping frame {frame.id}; unexpected depth size",
                      file=sys.stderr)
                continue
            depth = depth.reshape(h, w)

            image = Image.open(image_path).convert("RGB")
            if image.size != (w, h):
                image = image.resize((w, h))
            image = np.asarray(image)

            near = max(float(frame.depth_range.near), 1e-3)
            far = float(frame.depth_range.far)
            us, vs = np.meshgrid(np.arange(w), np.arange(h))
            valid = (depth > near) & (depth < far) & np.isfinite(depth)
            if not valid.any():
                continue
            d = depth[valid]
            u = us[valid].astype(np.float32)
            v = vs[valid].astype(np.float32)

            # Scaniverse uses the COLMAP camera convention (x right, y down,
            # z forward) and stores camera-to-world poses directly.
            cam_xyz = np.stack([
                (u - camera.px) / camera.f * d,
                (v - camera.py) / camera.f * d,
                d,
            ], axis=1)
            rotation = Rotation.from_quat(
                np.asarray(frame.transform.rotation)).as_matrix()
            translation = np.asarray(frame.transform.translation,
                                     dtype=np.float32)
            world = (cam_xyz @ rotation.T + translation).astype(np.float32)
            world = world @ transform.T + offset
            yield world, image[vs[valid], us[valid]]
        print(f"\r  frame {total}/{total} (100%)", file=sys.stderr)

    def write(chunks):
        if want_las:
            return _write_las(output, chunks, geo["lat0"], geo["lon0"],
                              geo["elev0"], scan.scan.createdAt)
        return _write_ply(output, chunks)

    if voxel_size and voxel_size > 0:
        kept_pts, kept_cols, n = [], [], 0
        for points, colors in frame_chunks():
            kept_pts.append(points)
            kept_cols.append(colors)
            n += 1
            if n % 100 == 0:
                points, colors = _voxel_downsample(
                    np.concatenate(kept_pts), np.concatenate(kept_cols),
                    voxel_size)
                kept_pts, kept_cols = [points], [colors]
        if not kept_pts:
            raise RuntimeError(f"No usable frames found in {scaniverse_dir}")
        points, colors = _voxel_downsample(
            np.concatenate(kept_pts), np.concatenate(kept_cols), voxel_size)
        total = write([(points, colors)])
    else:
        total = write(frame_chunks())
    if total == 0:
        raise RuntimeError(f"No usable frames found in {scaniverse_dir}")

    if geo:
        print(f"Georeferenced to ENU about lat={geo['lat0']:.7f}, "
              f"lon={geo['lon0']:.7f}, elev={geo['elev0']:.2f} m -- "
              f"{geo['n_fixes']} GPS fixes, horizontal fit RMS "
              f"{geo['rms']:.2f} m")
    if want_las:
        print(f"LAS coordinates: UTM, EPSG:"
              f"{_utm_epsg(geo['lat0'], geo['lon0'])}")
    print(f"Wrote {total:,} points to {output}")

 
