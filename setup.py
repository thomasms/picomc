"""Setup script for picomc package"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="picomc",
    version="0.2.0",
    author="Thomas Smith",
    description="A simple Monte Carlo simulator for neutron transport",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/thomasms/picomc",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "matplotlib>=3.3.0",
    ],
    extras_require={
        "endf": ["endf-parserpy>=0.7.0"],
    },
)
