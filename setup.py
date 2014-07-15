from setuptools import setup


extra = {}
f = open('README.rst', 'r')
try:
    extra['long_description'] = f.read()
finally:
    f.close()


setup(
    name='greenio',
    version='0.5.0',
    description="Greenlets for asyncio (PEP 3156).",
    url='https://github.com/1st1/greenio/',
    license='Apache 2.0',
    packages=['greenio'],
    install_requires=['greenlet'],
)
