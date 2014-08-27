from setuptools import setup, find_packages
from dockerfabric import __version__

setup(
    name='docker-fabric',
    version=__version__,
    packages=find_packages(),
    install_requires=['six', 'Fabric>=1.8.0', 'docker-py>=0.4.0', 'docker-map>=0.1.0'],
    license='MIT',
    author='Matthias Erll',
    author_email='matthias@erll.de',
    description='Integration of Docker into Fabric.',
    platforms=['OS Independent'],
    include_package_data=True,
)
