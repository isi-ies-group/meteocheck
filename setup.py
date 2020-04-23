# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 00:43:23 2020

@author: Ruben
"""

from setuptools import setup

setup_args = dict(
    name="meteocheck",
    version="0.1.0",
    url='http://github.com/isi-ies-group/meteocheck',
    author="Rubén Núñez",
    author_email="ruben.nunez@ies.upm.es",
    description="Quality control for meteo stations",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Windows",
    ],
    python_requires='>=3.6',
    packages=['meteocheck'],
    zip_safe=False,
    package_data={'': ['*.ini']},
    include_package_data=True,
)

install_requires = [
    'numpy',
    'pandas',
    'matplotlib',
    'keyring',
]

if __name__ == '__main__':
    setup(**setup_args, install_requires=install_requires)

