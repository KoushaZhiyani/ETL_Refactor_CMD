# ETL Refactor CMD

A production-grade, SOLID-compliant ETL pipeline for ingesting, transforming, and persisting sales data from Microsoft SQL Server. The pipeline implements hash-based change detection, incremental loading, and a fully composable transformation engine — all built on abstract interfaces and dependency injection.

---

## Overview

This pipeline processes sales transactions sourced from a SQL Server view (`AlirezaSales`) through a structured Extract → Transform → Load workflow. It supports:

- Incremental loading via row-count flags
- Hash-based change detection (insert / update / delete)
- Composable, step-based data transformation
- Persistent logging to both file and console
- Safe, whitelisted database access to prevent SQL injection

The codebase is designed for extensibility: new data sources, transformation rules, or storage backends can be introduced without modifying existing code.

---

## Features

- **Hash Synchronization** — Detects new, changed, and deleted rows using a dedicated `Fact_Hash` table; avoids full reloads
- **Incremental Load Flags** — `CheckFlag` and `CheckUpdateFlag` compute row-count deltas to determine whether a pipeline run is necessary
- **Composable Transformation Pipeline** — Discrete `Transformer` steps are chained via `TransformPipeline` and can be reordered or extended freely
- **Repository Abstraction** — All DB operations are hidden behind abstract interfaces (`SelectData`, `SaveData`, `UpdateData`, `DeleteData`)
- **SQL Injection Protection** — Table names are validated against a hardcoded whitelist before any query is executed
- **Dual-Output Logging** — Structured log output to both rotating file and terminal via configurable `LoggerConfigurator` and `TerminalLog`
- **Empty DataFrame Guards** — All persistence operations short-circuit safely when given empty data
- **Defensive Data Copying** — Transformers always operate on copies, preventing accidental mutation of upstream DataFrames
- **Bulk Insert Optimization** — Uses `fast_executemany=True` and `method='multi'` for high-throughput inserts

---

## Architecture

The project is organized into two layers:

```
┌────────────────────────────────────────────────┐
│              Application Layer                 │
│  extract_sell.py  transform_sell.py  save_sell.py │
│  (Use-case classes, orchestration logic)       │
└────────────────┬───────────────────────────────┘
                 │ depends on
┌────────────────▼───────────────────────────────┐
│            Infrastructure Layer                │
│  etl/preprocess.py   etl/hash.py               │
│  etl/save_database.py   etl/updater.py         │
│  etl/check_count_flag.py   etl/log.py          │
│  (Concrete implementations, DB drivers, utils) │
└────────────────────────────────────────────────┘
```

### Design Principles Applied

| Principle | Implementation |
|---|---|
| **Single Responsibility** | Each class has one clearly scoped responsibility (e.g., `EngineFactory` only creates engines) |
| **Open/Closed** | New extractors, transformers, or savers extend base classes without modifying existing code |
| **Dependency Inversion** | All components depend on ABCs, never concrete classes |
| **Strategy Pattern** | Hash check/create/update logic is interchangeable (`CheckHashSell`, `CreateHashSell`, `UpdateHashSell`) |
| **Repository Pattern** | Persistence is fully abstracted; the business layer never writes SQL directly |
| **Pipeline Pattern** | `TransformPipeline` composes `Transformer` steps sequentially |

---

## Data Flow

```
[SQL Server]
  └── AlirezaSales (view), InvcnoList, Fact_Recorder
            │
            ▼
     ExtractSellData
            │
            ▼
  CheckFlag / CheckUpdateFlag
  (row count delta → decide whether to proceed)
            │
            ▼
     ExtractHashData
  (AlirezaSales + Fact_Hash)
            │
            ▼
  create_hash() → per-row hash string (ID + netvalue)
            │
            ▼
  CheckHashSell.check()
  ├── rows_to_create  → CreateHashSell → INSERT Fact_Hash
  ├── rows_to_update  → UpdateHashSell → UPDATE Fact_Hash
  └── stale rows      → ExtraFinder   → DELETE Fact_Hash
            │
            ▼
  TransformPipeline
  ├── DropColumns          (remove unused columns)
  ├── SetValue             (add tag column, normalize dates)
  ├── RenameSellColumns    (apply column name mapping)
  ├── ExtractCustomerDf    (identify new customers)
  ├── SetValueCustomers    (assign default group values)
  └── MapVisitorCustomer   (resolve visitor IDs)
            │
            ▼
  SaveSellData        → INSERT Fact_Sell, Fact_Recorder
  SaveSellCustomer    → INSERT Dim_Custom, Bridge_Vistor_Customer
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Microsoft SQL Server with ODBC Driver 17
- Windows Authentication (Trusted Connection) configured for the target server

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ETL_Refactor_CMD.git
cd ETL_Refactor_CMD

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install pandas sqlalchemy pyodbc
```

### Verify ODBC Driver

```bash
python -c "import pyodbc; print(pyodbc.drivers())"
# Should include: 'ODBC Driver 17 for SQL Server'
```

---

## Configuration

Database connection is configured via `SqlServerEngineFactory`:

```python
from etl.save_database import SqlServerEngineFactory

factory = SqlServerEngineFactory()
engine = factory.create(
    server="YOUR_SERVER_NAME",
    database="YOUR_DATABASE_NAME"
)
```

The factory builds a Trusted (Windows Auth) connection. To use SQL authentication, modify the connection string in `SqlServerEngineFactory.create()`.

### Logger Configuration

```python
from etl.log import LoggerConfigurator, TerminalLog

log_config = LoggerConfigurator(
    dest_path="logs/etl_pipeline.log",
    formater="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = log_config.configure_log()
TerminalLog.create_handle(logger)  # Optional: also print to terminal
```

---

## Usage

### Running the Sales ETL Pipeline

```python
from etl.save_database import SqlServerEngineFactory, SelectDataSql, SaveDataSQL
from etl.log import LoggerConfigurator, TerminalLog
from extract_sell import ExtractSellData
from transform_sell import TransformSellData, HashSyncService, SqlHashRepository
from save_sell import SaveSellData
from etl.preprocess import TransformPipeline, DropColumns, SetValue, RenameSellColumns
from etl.hash import CheckHashSell, CreateHashSell, UpdateHashSell, RemoveExtraRows
from etl.save_database import UpdateDataSQL, DeleteDataSQL
from datetime import datetime

# 1. Setup logger
logger = LoggerConfigurator("logs/etl.log", "%(asctime)s - %(levelname)s - %(message)s").configure_log()
TerminalLog.create_handle(logger)

# 2. Setup DB engine
engine = SqlServerEngineFactory().create("SERVER_NAME", "DATABASE_NAME")
repo = SelectDataSql(engine)

# 3. Extract
extractor = ExtractSellData(repo, logger)
data_vw, invo_df, recorder_df = extractor.extract()

# 4. Hash sync
date_now = int(datetime.now().strftime("%Y%m%d"))
hash_repo = SqlHashRepository(
    save_obj=SaveDataSQL(),
    update_obj=UpdateDataSQL(),
    remove_obj=DeleteDataSQL(),
    connection=engine.connect()
)
hash_service = HashSyncService(
    hash_checker=CheckHashSell(repo.select_data("Fact_Hash")),
    hash_creator=CreateHashSell(date_now),
    hash_repository=hash_repo,
    log=logger
)
hash_service.sync(data_vw, date_now)

# 5. Transform
pipeline = TransformPipeline([DropColumns(), SetValue(), RenameSellColumns()])
transformer = TransformSellData(pipeline, logger)
transformed = transformer.transform(data_vw)

# 6. Save
with engine.begin() as conn:
    saver = SaveSellData(SaveDataSQL(), logger)
    saver.save({"Fact_Sell": transformed, "Fact_Recorder": recorder_df}, conn)
```

---

## Logging

The logging system supports dual output (file + terminal) and is fully configurable.

| Class | Responsibility |
|---|---|
| `PathGenerateLog` | Creates log directory tree if it does not exist |
| `LoggerConfigurator` | Attaches a `FileHandler` with custom format, level, and encoding |
| `TerminalLog` | Attaches a `StreamHandler` for real-time console output |

Log entries are named after the log file stem to allow multiple independent loggers in the same process. Duplicate handlers are prevented at setup time.

**Default format:**
```
2024-03-15 10:22:01,334 - etl_pipeline - INFO - Extracting sell data
2024-03-15 10:22:03,112 - etl_pipeline - INFO - Sell data extraction completed
```

Logs are written in UTF-8 and appended by default (`filemode="a"`).

---

## Error Handling

| Mechanism | Location | Behavior |
|---|---|---|
| **Table whitelist** | `SelectDataSql`, `UpdateDataSQL`, `DeleteDataSQL` | Raises `ValueError` for any unrecognized table name |
| **Empty DataFrame guards** | `SaveDataSQL`, `UpdateDataSQL`, `DeleteDataSQL` | Returns early; no DB call is made |
| **Missing key column check** | `UpdateDataSQL`, `DeleteDataSQL` | Raises `ValueError` if the key column is absent from the DataFrame |
| **Type coercion** | `filter_data()`, `CheckHashSell.check()` | Uses `pd.to_numeric(..., errors='coerce')` to convert to nullable `Int64`, silencing bad values |
| **Defensive copying** | All `Transformer` subclasses | Calls `.copy()` before mutation to protect upstream DataFrames |
| **Duplicate log handler prevention** | `LoggerConfigurator`, `TerminalLog` | Checks existing handlers before attaching new ones |
| **Exception re-raise** | `LoggerConfigurator.configure_log()` | Catches and re-raises with full traceback for upstream handling |
| **Bulk execution error propagation** | `UpdateDataSQL.update_data()` | Catches DB errors and re-raises; a logger hook is available but commented out for configuration flexibility |

---

## Project Structure

```
ETL_Refactor_CMD/
│
├── extract_sell.py          # Extraction use cases (BaseExtractor, ExtractSellData,
│                            #   ExtractCustomerData, ExtractHashData)
│
├── transform_sell.py        # Transformation use cases (BaseTransformer, TransformSellData,
│                            #   TransformCustomerData, HashSyncService, SqlHashRepository)
│
├── save_sell.py             # Persistence use cases (BaseSave, SaveSellData, SaveSellCustomer)
│
└── etl/                     # Shared infrastructure package
    ├── preprocess.py        # Atomic Transformer steps + TransformPipeline
    ├── hash.py              # Hash generation, comparison, sync strategies
    ├── save_database.py     # DB engine factory, select/save/update/delete implementations
    ├── updater.py           # CheckUpdateFlag (row-count comparison utility)
    ├── check_count_flag.py  # CheckFlag ABC + ReturnFlag (incremental load signal)
    └── log.py               # LoggerConfigurator, PathGenerateLog, TerminalLog
```

### Target Database Tables

| Table | Type | Description |
|---|---|---|
| `AlirezaSales` | View (source) | Main sales data source |
| `InvcnoList` | Reference | Invoice number reference list |
| `Fact_Sell` | Fact | Processed sales transactions |
| `Fact_Recorder` | Fact | Pipeline run tracking |
| `Fact_Hash` | Control | Hash values for change detection |
| `Fact_Return` | Fact | Return transactions |
| `Dim_Custom` | Dimension | Customer master data |
| `Dim_Visitor` | Dimension | Visitor data |
| `Bridge_Vistor_Customer` | Bridge | Visitor-to-customer ID mapping |
| `Dim_Dates` | Dimension | Date dimension |
| `Dim_Product` | Dimension | Product dimension |

---

## Future Improvements

- **Configuration file support** — Externalize server name, database name, date ranges, and table names into a `config.yaml` or `.env` file rather than hardcoding them
- **Inject table names in `SqlHashRepository`** — The `"Fact_Hash"` table name is currently hardcoded inside `save()` and `update()`; it should be injected at construction time
- **Orchestration entry point** — Add a `main.py` or CLI script that wires all dependencies together and drives the full pipeline end-to-end
- **Unit test suite** — The abstract-interface design is highly testable; add `pytest` tests with mock repositories for each use case
- **Column mapping population** — `RenameSellColumns.COLUMN_MAPPING` is currently empty; populate with the actual Persian-to-English column name mappings
- **Retry logic** — Add configurable retry/backoff for transient SQL Server connection failures
- **Docker support** — Containerize the pipeline with a `Dockerfile` for consistent deployment across environments
- **Schema validation** — Add input DataFrame schema validation (e.g., with `pandera`) at extraction boundaries to catch upstream data contract violations early
- **Async/parallel extraction** — `ExtractSellData` queries three tables sequentially; these could be fetched concurrently using `asyncio` or `ThreadPoolExecutor`
- **Monitoring integration** — Emit structured metrics (row counts, run duration, hash delta) to a monitoring system (e.g., Prometheus, Azure Monitor)
