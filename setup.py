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
        'pylzfse',
        'protobuf',
        'defopt',
        'Pillow',
      ],
      zip_safe=False)

