import setuptools
from pathlib import Path

##### THINGS TO EDIT STARTS #####

# short description of your project
description = "python toolbox"

# list of packages to install
install_requires = []

# additional classifiers
classifiers = []

##### THINGS TO EDIT ENDS #####

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("version", "r") as fh:
    version = fh.read()

projectname = Path.cwd().name

setuptools.setup(
    name=projectname,
    version=version,
    author="Balint Takacs",
    author_email="takbal@gmail.com",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/takbal/" + projectname,
    package_dir={"": "src"},
    packages=setuptools.find_namespace_packages(where="src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ] + classifiers,
    python_requires='>=3.8',
    install_requires=install_requires
)
