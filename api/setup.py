from setuptools import setup, find_packages


def read_requirements():
    """Read requirements from requirements.txt"""
    with open("requirements.txt") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="esco-skill-extractor",
    version="2.0.0",
    packages=find_packages(),
    install_requires=read_requirements(),
    include_package_data=True,
    package_data={"": ["data/*.bin", "data/*.npy"]},
    author="Enhanced by Claude Code",
    description="Extract ESCO skills and occupations with rich cross-referenced data using BGE-M3 embeddings",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License", 
        "Operating System :: OS Independent",
        "Framework :: FastAPI",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "esco-api=main:main",
        ],
    },
)