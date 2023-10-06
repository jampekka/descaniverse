from . import scaniverse_pb2
from google.protobuf.json_format import MessageToDict
from pathlib import Path
import sys
import json
from typing import Union, TextIO, Optional
import os.path
import shutil

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
            'directory': self.directory,
            'scan': json_format.MessageToDict(self.scan),
            'frames': json_format.MessageToDict(self.frames)
                }

class FakePath:
    def __init__(self, file, name):
        self.file = file
        self.name = name

    def __str__(self):
        return self.name

    def open(self, *args, **kwargs):
        return self.file


def scaniverse_to_json(scaniverse_dir: Path, output: Path=FakePath(sys.stdout, "STDOUT")):
    """Converts Scaniverse metadata as-is to JSON"""
    scan = ScaniverseRawData(scaniverse_dir)
    if output is None:
        output = sys.stdout
    else:
        output = output.open('w')
    json.dump(scan.as_dict(), output, indent=2)
    output.write('\n')

def scaniverse_to_nerfstudio(scaniverse_dir: Path, output_dir: Path,
                             depth: bool=True, copy_images: bool=True):
    """Converts a Scaniverse scan to nerfstudio format"""
    # TODO: Currently reads only large frames
    scan = ScaniverseRawData(scaniverse_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir/"transforms.json"
    output_image_dir = output_dir/"images_large"
    output_depth_dir = output_dir/"depth"
    
    input_image_dir = scaniverse_dir/"imgl"
    input_depth_dir = scaniverse_dir/"depth"

    if copy_images: output_image_dir.mkdir(exist_ok=True)
    if depth: output_depth_dir.mkdir(exist_ok=True)
    
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
        data = dict(
            px=camera.px*small_to_large,
            py=camera.py*small_to_large,
            fl_x=focal_length,
            fl_y=focal_length,
        )

        input_image_path = input_image_dir/f"{file_base}.jpg"
        if copy_images:
            dst = output_image_dir/input_image_path.name
            shutil.copyfile(input_image_path, dst)
            data['file_path'] = str(dst.relative_to(output_dir))
        else:
            # TODO: Uses absolute
            data['file_path'] = os.path.relpath(input_image_path, output_dir)
        
        data['scaniverse_frame'] = MessageToDict(frame)
        frames.append(data)
    
    json.dump(transforms, open(output_file, 'w'), indent=2)
    #small_to_big_w = scan.
    from pprint import pprint
    #pprint(transforms, sort_dicts=False)
    #transforms = {
    #    
    #        }

 