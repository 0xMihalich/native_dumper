# Version History

## 0.3.3.1

* Improve chunk_query function

## 0.3.3.0

* Improve Multiquery decorator

## 0.3.2.3

* Update depends light-compressor==0.0.1.9
* Update depends nativelib==0.2.2.1
* Refactor variable info.precission -> info.precision

## 0.3.2.2

* Fix chunk_query for ignoring semicolons inside string literals

## 0.3.2.1

* Update depends nativelib==0.2.1.3

## 0.3.2.0

* Update depends light-compressor==0.0.1.8
* Update depends nativelib==0.2.1.2
* Fix multiquery wrapper
* Add transfer_diagram and DBMetadata to make log diagrams
* Add _dbmeta attribute
* Add log output diagram
* Add auto upload to pip

## 0.3.1.2

* Add NativeDumper.dbname attribute with constant string "clickhouse"
* Update setup.cfg

## 0.3.1.1

* Add wheels automake
* Update Cargo.toml depends
* Update depends nativelib==0.2.1.1
* Update pyo3http
* Change pyo3http.pyi
* Refactor HTTPCursor

## 0.3.1.0

* Add pyo3http.pyi files for pyo3 modules descriptions
* Add close() method to pyo3http.HttpSession
* Update MANIFEST.in
* Update depends setuptools>=80.9.0
* Update depends wheel>=0.45.1
* Update depends setuptools-rust>=1.12.0
* Update depends light-compressor==0.0.1.7
* Update depends nativelib==0.2.1.0

## 0.3.0.4

* Update depends nativelib==0.2.0.7
* Add internal methods __read_dump, __write_between and __to_reader to force kwargs creation

## 0.3.0.3

* Update requirements.txt depends nativelib==0.2.0.5
* Update requirements.txt depends light-compressor==0.0.1.6
* Update file_writer set chunk size to 1MB
* Add check error to execute function
* Add readed and sending size output into log
* Fix logger create folder in initialize
* Fix error code detector

## 0.3.0.2

* Change log message
* Improve refresh database after write

## 0.3.0.1

* Add attribute is_connected to HTTPCursor
* Add attribute server_version to HTTPCursor
* Add close files after read/write operations
* Add special error 92 (EMPTY_DATA_PASSED) when server sending empty data
* Improve login error
* Improve other errors
* Improve read method from another database
* Change log messages for read operations
* Update requirements.txt depends nativelib==0.2.0.4
* Update requirements.txt depends light-compressor==0.0.1.5

## 0.3.0.0

* Redistribute project directories
* Update requirements.txt
* Update README.md
* Change requests to rust pyo3 class
* Change methods & work strategy
* Readed dumps now not depends from compressed codecs
* Add support for write between with differents Databases (not ClickHouse only)
* Add MIT License

## 0.2.0.1

* Update depends in requirements.txt
* Change compressors to light-compressor
* Speed-up stream read

## 0.2.0.0

* Add nativelib to requirements.txt
* Add HTTPCursor.metadata(table) method for describe table columns
* Add NativeDumper.to_reader(query, table_name) method for return NativeReader object
* Add NativeDumper.from_rows(dtype_data, table_name) method for write table from python list
* Add NativeDumper.from_pandas(data_frame, table_name) method for write table from pandas.DataFrame
* Add NativeDumper.from_polars(dtype_data, table_name) method for write table from polars.DataFrame
* Update README.md

## 0.0.1.0

First version of the library native_dumper

* Read and write native format between clickhouse server and file
* Write native between clickhouse servers
