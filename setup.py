from distutils.core import setup


setup(
    name='greenio',
    description="Greenlet based implementation of PEP 3156 event loop.",
    url='https://github.com/1st1/greenio/',
    license='Apache 2.0',
    packages=['greenio'],
    install_requires=['greenlet'],
)
