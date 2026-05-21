from setuptools import setup

setup(name='descaniverse',
      version='0.1',
      description='Read and convert Scaniverse raw data',
      url='http://github.com/jampekka/descaniverse',
      author='Jami Pekkanen',
      author_email='jami.pekkanen@gmail.com',
      license='AGPLv3',
      packages=['descaniverse'],
      scripts=['bin/descaniverse'],
      # TODO: We could get by with lighter dependencies
      install_requires=[
        'numpy',
        'scipy',
        'pyliblzfse',
        'protobuf',
        'defopt',
        'Pillow',
      ],
      # Optional: only needed for `to_pointcloud` LAS output.
      extras_require={
        'las': ['laspy', 'pyproj'],
      },
      zip_safe=False)

