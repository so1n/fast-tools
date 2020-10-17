import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fast-tools",
    version="1.0.0",
    author="so1n",
    author_email="so1n897046026@gmail.com",
    description="fast-tools is a FastApi/Starlette toolset, Most of the tools can be used in FastApi/Starlette, a few tools only support FastApi which is divided into the lack of compatibility with FastApi",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/so1n/fast-tools",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
