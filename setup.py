from distutils.core import setup


setup(
    name='greentulip',
    description="Greenlet based implementation of PEP 3156 event loop.",
    url='https://github.com/1st1/greentulip/',
    license='Apache 2.0',
    packages=['greentulip'],
    install_requires=['greenlet'],
)
