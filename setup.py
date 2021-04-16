import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nimbo",  # Replace with your own username
    version="0.1.4",
    author="NimboSH, Ltd.",
    author_email="support@nimbo.sh",
    description="Run machine learning jobs on AWS with a single command.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/seuqaj114/nimbo",
    project_urls={
        "Bug Tracker": "https://github.com/seuqaj114/nimbo/issues",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: Free for non-commercial use",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3"
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(
        where="src",
        exclude=["tests", "ami"]
    ),
    package_data={"nimbo": ["scripts/*.sh"]},
    include_package_data=True,
    entry_points = {
        'console_scripts': ['nimbo=nimbo.main:cli'],
    },
    python_requires=">=3.6",
    install_requires=[
        "awscli>=1.19<2.0",
        "boto3>=1.17",
        "requests>=2.25",
        "click>=7.0",
   ],
)
