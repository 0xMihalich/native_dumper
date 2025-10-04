# Version History

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
