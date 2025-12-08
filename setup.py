from setuptools import setup, find_packages
from setuptools_rust import RustExtension

setup(
    name="native-dumper",
    version="0.3.4.7",
    description=(
        "Library for read and write Native format between Clickhouse and file."
    ),
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="0xMihalich",
    author_email="bayanmobile87@gmail.com",
    url="https://github.com/0xMihalich/native_dumper",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    rust_extensions=[
        RustExtension(
            "native_dumper.common.pyo3http",
            path="src/native_dumper/common/pyo3http/Cargo.toml",
            debug=False,
        )
    ],
    install_requires=[
        "light-compressor==0.0.2.1",
        "nativelib==0.2.2.4",
        "sqlparse>=0.5.4",
    ],
    zip_safe=False,
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
)
