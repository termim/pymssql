# -*- coding: utf-8 -*-

import os
import os.path as osp
import struct
import sys

from setuptools import Extension, setup
from setuptools.dist import Distribution
Distribution(dict(setup_requires='Cython>=0.29.1'))
from Cython.Build import cythonize

# 32 bit or 64 bit system?
bitness = struct.calcsize("P") * 8

include_dirs = []
libraries = ['sybdb']
library_dirs = []

prefix = None
if os.getenv('PYMSSQL_FREETDS'):
    prefix = os.getenv('PYMSSQL_FREETDS')
elif osp.exists("/usr/local/includes/sqlfront.h"):
    prefix = "/usr/local"
if prefix:
    include_dirs = [ osp.join(prefix, "include") ]
    if bitness == 64 and osp.exists(osp.join(prefix, "lib64")):
        library_dirs = [ osp.join(prefix, "lib64") ]
    else:
        library_dirs = [ osp.join(prefix, "lib") ]

if os.getenv('PYMSSQL_FREETDS_INCLUDEDIR'):
    include_dirs = [ os.getenv('PYMSSQL_FREETDS_INCLUDEDIR') ]

if os.getenv('PYMSSQL_FREETDS_LIBDIR'):
    library_dirs = [ os.getenv('PYMSSQL_FREETDS_LIBDIR') ]

print("include_dirs=", include_dirs)
print("library_dirs=", library_dirs)


_extra_compile_args = ['-DMSDBLIB']

extensions = [
    Extension("*", ["src/*.pyx"],
              extra_compile_args = _extra_compile_args,
              #extra_link_args=['-static'], CFLAGS=-fPIC
              include_dirs=[ str(x) for x in include_dirs ],
              libraries=libraries,
              library_dirs=[ str(x) for x in library_dirs ],
              ),
]
setup(
    name='pymssql',
    use_scm_version = {
        "write_to": "src/version.h",
        "write_to_template": '#define PYMSSQL_VERSION "{version}"',
        "local_scheme": "no-local-version",
    },
    description = 'DB-API interface to Microsoft SQL Server for Python. (new Cython-based version)',
    long_description = open('README.rst').read() +"\n\n" + open('ChangeLog_highlights.rst').read(),
    ext_modules=cythonize(extensions, language_level=sys.version_info.major),
    zip_safe=False,
    setup_requires=['setuptools_scm', 'Cython'],
    tests_require=['pytest', 'pytest-timeout', 'unittest2', 'pathlib2'],
    )
