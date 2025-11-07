from setuptools import setup, find_packages


def read_requirements():
    """Read requirements from requirements.txt, filtering comments"""
    with open("requirements.txt") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="esco-skill-extractor",
    version="0.2.0",
    packages=find_packages(),
    install_requires=read_requirements(),
    include_package_data=True,
    package_data={"esco_skill_extractor": ["data/*.csv"]},
    author="Konstantinos Petrakis",
    author_email="konstpetrakis01@gmail.com",
    description="Extract ESCO skills and ISCO occupations from texts using FastAPI",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/KonstantinosPetrakis/esco-skill-extractor",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: FastAPI",
    ],
    python_requires=">=3.8",
)
