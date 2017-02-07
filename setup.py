"""   
desc:  Setup script for 'papa' micropython compatible package.
auth:  Craig Wm. Versek (cversek@gmail.com)
date:  2017-02-06
notes: install with "sudo python setup.py install"
"""


import platform, os, shutil


PACKAGE_METADATA = {
    'name'         : 'pawpaw',
    'version'      : 'dev',
    'author'       : "Craig Versek",
    'author_email' : "cversek@gmail.com",
}
    
PACKAGE_SOURCE_DIR = '.'
MAIN_PACKAGE_DIR   = 'pawpaw'
MAIN_PACKAGE_PATH  = os.path.abspath(os.sep.join((PACKAGE_SOURCE_DIR,MAIN_PACKAGE_DIR)))

INSTALL_REQUIRES = []


###############################################################################
# MAIN
###############################################################################
if __name__ == "__main__":
    from setuptools import setup, find_packages

    setup(
          #packages to install
          package_dir  = {'':PACKAGE_SOURCE_DIR},
          packages     = find_packages(PACKAGE_SOURCE_DIR),
          **PACKAGE_METADATA
    )
