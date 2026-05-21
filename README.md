# descaniverse - read and convert Scaniverse raw data

😎 [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0) 😎

descaniverse is a Python library and CLI tools for reading and converting [Scaniverse](https://scaniverse.com/) raw data.
The data format is [reverse engineered](./reverse_engineering/) and thus all data is not necessarily available.

## Getting Scaniverse raw data

[Scaniverse optionally records "raw data"](https://blog.scaniverse.com/save-raw-data-for-future-processing-e427b23600b6). This has to be enabled for this to work. Non-raw data can be mostly exported directly from the app.

Scaniverse doesn't support exporting raw data and it can't be read from the device using the usual
tools (e.g. [ifuse](https://github.com/libimobiledevice/ifuse)) to read files from iPhone/iPad¹.

With older iOS versions the data can be accessed by creating a backup of the device using [idevicebackup2](https://libimobiledevice.org/))
and extracting it using [ideviceunback](https://github.com/inflex/ideviceunback). The scans
can be found in `/Library/Application Support/scans/` of the extracted backup. For newer iOS versions try [iOSbackup](https://pypi.org/project/iOSbackup/).

A backup made with [iMazing](https://imazing.com/) works too: it is a standard (optionally encrypted) iOS backup, so the scans can be extracted from it with e.g. [iphone_backup_decrypt](https://github.com/jsharkey13/iphone_backup_decrypt) — no iMazing licence required.

Alternatively, you can probably access these easily on jailbroken device. If you
know a nicer way to access these files (without jailbreak), please leave an issue.

## Install

```console
pip install git+https://github.com/jampekka/descaniverse
```

## Usage

A CLI interface is included as `descaniverse` runnable.

```console
usage: descaniverse [-h] {to_json,to_nerfstudio,to_pointcloud} ...

positional arguments:
  {to_json,to_nerfstudio,to_pointcloud}
    to_json             Converts Scaniverse metadata as-is to JSON
    to_nerfstudio       Converts a Scaniverse scan to nerfstudio format
    to_pointcloud       Converts a Scaniverse scan to a colored point cloud

optional arguments:
  -h, --help            show this help message and exit
```

`to_json`, `to_nerfstudio` and `to_pointcloud` all accept `--append-scan-name` (append the scan's sanitized name to the output) and `--prefix-timestamp` (prefix the output name with the scan's capture time, formatted `YYYYMMDD-HHMMSS`).

`to_pointcloud` additionally accepts `--z-up` (Z-up output, e.g. for CloudCompare) and `--georeference` (place the cloud in a real-world East-North-Up frame using the recorded GPS track). Its density is controlled by `--voxel-size` (downsampling cell size in meters) and `--max-frames`; `--voxel-size 0 --max-frames 0` keeps every point at full resolution.

Recommended density: the Apple LiDAR depth maps are only 256×192, so the native point spacing is roughly 1 cm at typical scanning range. `--voxel-size 0.01 --max-frames 0` captures essentially all real detail and is the practical maximum; `--voxel-size 0.02` (the default) is a lighter general-purpose choice. Smaller voxel sizes — or `--voxel-size 0` — mostly add duplicate and noise-level points and can yield hundreds of millions of points on a longer scan.

Giving the `to_pointcloud` output a `.las` extension instead of `.ply` writes a georeferenced LAS file in the local UTM zone (with the scan's capture date in the LAS header), ready to drop into QGIS, Cesium or other GIS tools. This needs the optional extras: `pip install descaniverse[las]`.

##
