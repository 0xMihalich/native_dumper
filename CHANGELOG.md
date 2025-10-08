# Version History

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
