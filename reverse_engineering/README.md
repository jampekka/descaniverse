# Reverse-engineering of Scaniverse raw data format

The reverse engineered Scaniverse version was 2.1.4 but the data for (most) testing was recorded with 2.1.8. It's unknown whether the data format may change between Scaniverse versions.

Scaniverse stores each scanning session as a directory in `/Library/Application Support/scans/`.
The directory entries of interest for the raw data are:

* `scan.pb`: Protocol buffer file containing metadata if the scanning session. Partially reverse engineered.
  * Contributions appreciated for further reverse engineering.
* `frames.pb`: Protocol buffer file containing metadata on each recorded frame. Mostly reverse engineered.
  * Contributions appreciated for further reverse engineering.
* `imgl/`: Directory of high resolution JPEG images.
* `img/`: Directory of low resolution JPEG images. Presumably simply rescaled from the high resolution images.
* `depth/`: Directory of depth images (extension .dmp, probably meaning memory dump). Lzfse compressed raw binary of float16 values that represent the depth in meters, but 0 means unknown depth. Reshape to the known depth image resolution. These sometimes don't contain enough values to construct the depth image for unknown reasons. I've just skipped these frames.

## Protocol buffer formats

The protocol buffer formats were reverse engineered with the help of [blackboxprotobuf](https://github.com/nccgroup/blackboxprotobuf) and [resymbol](https://github.com/paradiseduo/resymbol). Resymbol extracts Swift class structure (see the [Scaniverse.headers](Scaniverse.headers) file) from the ([Apple Fairplay DRM decrypted](https://decrypt.day/app/id1541433223)) `Scaniverse` binary of the iOS app.

The `scan.pb` message class is `ScanProto` but its structure is defined in the (larger) `_StorageClass` class. The structure doesn't seem to match exactly the protocol buffer structure but most fields of it can be figured out from this.

For `frames.pb` the class is `FramesProto`. Its `frames` field is an array of `FrameProto` objects but again this is defined in the (smaller) `_StorageClass` class. This has been more or less fully reverse engineered.

The main classess contain fields of other `*Proto` classes. These are mostly self-explanatory, with some detailed below.

Camera poses are stored in `AffineTransformProto` objects. `rotation` is a quaternion in scalar-last format (x, y, z, w) and `translation` is the camera 3D location in meters(?). The coordinate system is that of OpenCV/COLMAP (+X right, +Y down, +Z look-at). The coordinates are "camera-to-world", i.e. `translation` is the location in the world-space and `rotation` is the rotation around the camera's origin.

Camera intrinsics (for the low resolution images) are defined for each frame in the `camera` field of the `FrameProto` as `CameraParamsProto` objects. The intrinsics have variable principal points (`px` and `py`) and focal length `f` (due to changing focus and maybe image stabilization?). There's no separate focal length for x-axis (image width) and y-axis (image height) so presumably this is shared (COLMAP estimates the same focal length for both axes). The `FramesProto` in the class dump has a `k` (presumably distortion coefficient) but this doesn't seem to be included in the `frames.pb` data. COLMAP estimates `k1` of about -0.0147 although with assumption of image-center principal point and fixed focal length. Using zero distortion seems to work fine, the images are likely undistorted for the image pixels to match the depth image pixels.
