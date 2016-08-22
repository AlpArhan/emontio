
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='emontio_web',
    version='1.0.0',
    description='Emontio: Empowering market analysis with emotion recognition.',
    long_description=long_description,
    url='https://github.com/AlpArhan/emontio',
    license='GNU GENERAL PUBLIC LICENSE'
)
