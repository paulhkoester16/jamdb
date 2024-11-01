from setuptools import setup, find_packages

setup(
    name="jamdb",
    version="0.0.1",
    description="Database and queries for keeping track of what I've played, where I played it, who I played it with.",
    author="paul koester",
    author_email="paulhkoester@gmail",
    packages=find_packages(exclude=("tests", "docs")),
    test_suite="tests",
    #include_package_data=True,
    #package_data={"": ["data/*.csv", "data/*.json", "data/*.txt", "data/*.png"]},
    #zip_safe=False
)

