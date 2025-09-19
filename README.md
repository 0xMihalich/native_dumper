# NativeDumper

Library for read and write Native format between Clickhouse and file

## Examples

### Initialization

```python
from native_dumper import (
    CompressionMethod,
    CHConnector,
    NativeDumper,
)

connector = CHConnector(
    host = <your host>,
    dbname = <your database>,
    user = <your username>,
    password = <your password>,
    port = 8123,
)

dumper = NativeDumper(
    connector=connector,
    compression_method=CompressionMethod.ZSTD,  # or CompressionMethod.LZ4 or CompressionMethod.NONE
)
```

### Read dump from PostgreSQL into file

```python
file_name = "native.zstd"
# you need define one of parameter query or table_name
query = "select ..."  # some sql query
table_name = "default.test_table"  # or some table

with open(file_name, "wb") as fileobj:
    dumper.read_dump(
        fileobj,
        query,
        table_name,
    )
```

### Write dump from file into PostgreSQL

```python
file_name = "native.zstd"
# you need define one of parameter table_name
table_name = "default.test_table"  # some table

with open(file_name, "rb") as fileobj:
    dumper.write_dump(
        fileobj,
        table_name,
    )
```

### Write from PostgreSQL into PostgreSQL

Same server

```python

table_dest = "default.test_table_write"  # some table for write
table_src = "default.test_table_read"  # some table for read
query_src = "select ..."  # or some sql query for read

dumper.write_between(
    table_dest,
    table_src,
    query_src,
)
```

Different servers

```python

connector_src = CHConnector(
    host = <host src>,
    dbname = <database src>,
    user = <username src>,
    password = <password src>,
    port = 8123,
)

dumper_src = NativeDumper(connector=connector_src)

table_dest = "default.test_table_write"  # some table for write
table_src = "default.test_table_read"  # some table for read
query_src = "select ..."  # or some sql query for read

dumper.write_between(
    table_dest,
    table_src,
    query_src,
    dumper_src.cursor,
)
```

### Open Native file format

Get info from my another repository https://github.com/0xMihalich/nativelib

## Installation

### From pip

```bash
pip install native_dumper
```

### From local directory

```bash
pip install .
```

### From git

```bash
pip install git+https://github.com/0xMihalich/native_dumper
```
