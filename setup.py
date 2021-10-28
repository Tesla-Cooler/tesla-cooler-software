"""Use this file to install tesla_cooler as a module"""

from distutils.core import setup
from setuptools import find_packages
from typing import List


def prod_dependencies() -> List[str]:
    """
    Pull the dependencies from the requirements dir
    :return: Each of the newlines, strings of the dependencies
    """
    with open("./requirements/prod.txt", "r") as file:
        return file.read().splitlines()


setup(
    name="tesla_cooler",
    version="0.2.1",
    description=(
        "Firmware for a Raspberry Pi Pico to drive fans and cool NVIDIA Tesla compute GPUs."
    ),
    author="Devon Bray",
    author_email="dev@esologic.com",
    packages=find_packages(),
    install_requires=prod_dependencies(),
)
