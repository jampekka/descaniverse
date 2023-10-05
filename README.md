# descaniverse - read and convert Scaniverse raw data

😎 [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0) 😎

descaniverse is a Python library and CLI tools for reading and converting [Scaniverse](https://scaniverse.com/) raw data.
The data format is [reverse engineered](./reverse_engineering/)¹ and thus all data is not necessarily available.

## Getting Scaniverse raw data

Scaniverse doesn't support exporting raw data and it can't be read from the device using the usual
tools (e.g. [ifuse](https://github.com/libimobiledevice/ifuse)) to read files from iPhone/iPad¹.
However, the data can be accessed by creating a backup of the device¹ (using [idevicebackup2](https://libimobiledevice.org/))
and extracting it using [ideviceunback](https://github.com/inflex/ideviceunback)¹. The scans
can be found in `/Library/Application Support/scans/` of the extracted backup.

Alternatively, you can probably access these easily on jailbroken¹ device. If you
know a nicer way to access these files (without jailbreak), please leave an issue.

## Install

```console
pip install git+https://github.com/jampekka/descaniverse
```

## Usage

TODO

##

<details>
<summary>1.</summary>

## Rant 🖕

Aren't walled gardens, closed source, DRM, war on general purpose computing etc. great?

If you think you need the LiDAR data (you probably don't if you do something like NeRF or photogrammetry),
iPhone/iPad seems to be unfortunately the only (integrated) option at the moment. Open Source alternatives
to Scaniverse are [ScanKit](https://github.com/Kenneth-Schroeder/ScanKit)
or [RTAB-Map](http://introlab.github.io/rtabmap/). [Polycam](https://poly.cam/) is closed source (and nagware),
but at least it lets you access your data.

A good alternative is to use Android and some ARCore/Tango recorder like [RTAB-Map](https://github.com/introlab/rtabmap/).
The LiDAR is mostly a gimmic anyway, with quite poor resolution, accuracy and range.
</details>
