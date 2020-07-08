import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="woma",
    packages=setuptools.find_packages(),
    version="1.0",
    description="WorldMaker",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sergio Ruiz-Bonilla, Jacob Kegerreis",
    author_email="sergio.ruiz-bonilla@durham.ac.uk",
    url="https://github.com/srbonilla/WoMa",
    download_url="https://github.com/srbonilla/WoMa/archive/1.0.tar.gz",
    project_urls={
        "Paper": "https://arxiv.org/abs/2007.02965",
        "Group": "http://icc.dur.ac.uk/giant_impacts",
        "SEAGen": "https://github.com/jkeger/seagen",
    },
    license="GNU GPLv3+",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Development Status :: 4 - Beta",
    ],
    python_requires=">=3",
    install_requires=["seagen", "numpy", "numba", "h5py"],
    package_data={"woma": ["data/*.txt", "data/*.npy"]},
    keywords=[
        "profile spinning rotating planet interior particle SPH initial conditions"
    ],
)
