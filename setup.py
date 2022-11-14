import setuptools


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="giphon",
    author="Gabriel Creti",
    author_email="gabrielcreti@gmail.com",
    description="Copy locally a Gitlab group or instance",
    keywords="gitlab, clone, copy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kabooboo/giphon",
    project_urls={
        "Documentation": "https://github.com/kabooboo/giphon",
        "Bug Reports": "https://github.com/kabooboo/giphon/issues",
        "Source Code": "https://github.com/kabooboo/giphon",
        # 'Funding': '',
        # 'Say Thanks!': '',
    },
    package_dir={"": "giphon"},
    packages=setuptools.find_packages(where="src"),
    classifiers=[
        # see https://pypi.org/classifiers/
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=open("requirements.txt").readlines(),
    extras_require={
        "test": ["pytest"],
    },
    entry_points={
        "console_scripts": [
            "run=giphon:main",
        ],
    },
)
