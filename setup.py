import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sapy",
    version="0.0.1",
    author="Zak Kohler",
    author_email="zak@zakkohler.com",
    description="SAP-1 emulator",
    long_description=long_description,
    packages=setuptools.find_packages(),
)
