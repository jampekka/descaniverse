# descaniverse - read and convert Scaniverse raw data

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0) 

descaniverse is a Python library and CLI tools for reading and converting [Scaniverse](https://scaniverse.com/) raw data.

## Getting Scaniverse raw data

Scaniverse doesn't support exporting raw data and it can't be read from the device using the usual
tools (e.g. [ifuse](https://github.com/libimobiledevice/ifuse)) to read files from iPhone/iPad.


<!--
 ## Rant 🖕

I wasted quite a bit of time on this. Closed software and platforms are a major hinderance
for technological and societal progress. Apple is of course especially shitty in this (and many other aspects)
and I encourage everybody to boycott them when feasible. In general avoid closed source
software and closed down devices.

I regret getting an iPhone for the project I needed this hackery for and I regret using Scaniverse.
If you think you need the LiDAR data (you probably don't if you do something like NeRF or photogrammetry),
iPhone/iPad seems to be unfortunately the only option, but
even then you're better off with open source like [ScanKit](https://github.com/Kenneth-Schroeder/ScanKit)
or [RTAB-Map](http://introlab.github.io/rtabmap/). [Polycam](https://poly.cam/) is closed source (and nagware),
but at least it lets you access your data.

You are probably better off using Android and some ARCore/Tango recorder like [RTAB-Map](https://github.com/introlab/rtabmap/).
The LiDAR is mostly a gimmic anyway, with quite poor resolution and accuracy.
-->
