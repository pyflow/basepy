import re
import ast
from setuptools import setup, find_packages

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('basepy/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

with open('README.md', 'rb') as f:
    long_description = f.read().decode('utf-8')

packages = ['basepy']
packages.extend(map(lambda x: 'basepy.{}'.format(x), find_packages('basepy')))

setup(
    name='basepy',
    version=version,
    url='https://github.com/pyflow/basepy/',
    license='MIT',
    author='Wei Zhuo',
    author_email='zeaphoo@qq.com',
    description='Base library of python 3.6+ and asyncio, include log, config, event, metric etc.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=packages,
    include_package_data=False,
    zip_safe=False,
    platforms='any',
    install_requires=["toml", "python-box"],
    extras_require={
        'dev': [
            'pytest>=3',
            'mock',
            'pyyaml'
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    python_requires='>=3.6',
    entry_points='''
    '''
)
