import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nimbo",  # Replace with your own username
    version="0.2.11",
    author="NimboSH, Ltd.",
    author_email="support@nimbo.sh",
    description="Run machine learning jobs on AWS with a single command.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nimbo-sh/nimbo",
    project_urls={"Bug Tracker": "https://github.com/nimbo-sh/nimbo/issues"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    package_data={"nimbo": ["scripts/*.sh"]},
    include_package_data=True,
    entry_points={"console_scripts": ["nimbo=nimbo.main:cli"]},
    python_requires=">=3.6",
    install_requires=[
        "awscli>=1.19<2.0",
        "boto3>=1.17",
        "requests>=2.25",
        "click>=7.0",
        "pyyaml>=5.3.0",
        "pydantic>=1.7.0",
        "rich>=10.1.0",
    ],
)
