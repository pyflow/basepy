import re
import ast
from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('basepy/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name='basepy',
    version=version,
    url='https://github.com/pyflow/basepy/',
    license='MIT',
    author='Wei Zhuo',
    author_email='zeaphoo@qq.com',
    description='A base library for python 3.6+ and asyncio',
    long_description='Base library of python , include log, config, event, metric etc. ',
    packages=['basepy'],
    include_package_data=False,
    zip_safe=False,
    platforms='any',
    install_requires=['msgpack', "toml", "python-box<4.0.0", "PyYAML"],
    extras_require={
        'dev': [
            'pytest>=3',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    entry_points='''
    '''
)
