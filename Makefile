descaniverse/scaniverse_pb2.py: scaniverse.proto
	protoc --proto_path . --python_out=descaniverse/ scaniverse.proto
