import os

version_file = open(os.path.join(os.path.dirname(__file__), '..', 'VERSION'))
__version__ = version_file.read().strip()