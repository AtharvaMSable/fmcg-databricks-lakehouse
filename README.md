# FMCG Data Integration Pipeline: End-to-End Databricks Solution

## 1. Project Overview
This project addresses a complex data engineering challenge following the acquisition of "Sports Bar" (a nutrition startup) by "AtliQ" (a mature sporting goods manufacturer). The objective was to integrate the disparate, file-based data systems of the acquired company into AtliQ's established enterprise data warehouse to enable unified analytics.

The solution creates a scalable ETL pipeline using **Databricks** and **Unity Catalog**, ingesting raw CSV data from **AWS S3** and processing it through a **Medallion Architecture** (Bronze, Silver, Gold). The pipeline handles historical backfills and incremental daily loads using **Delta Lake** features like Change Data Feed (CDF) and `MERGE` operations.

## 2. Architecture
The system follows a Lakehouse architecture pattern leveraging cloud object storage and managed compute.

**Text-Based Architecture View:**

```
[AWS S3: Landing Zone] 
       | (Ingest Raw CSVs)
       v
[Databricks: Bronze Layer] 
    - Raw Delta Tables (External)
    - Schema Inference
       | (Clean, Deduplicate, Normalize)
       v
[Databricks: Silver Layer] 
    - Cleaned Delta Tables (External)
    - Enforce Schema & Data Quality
       | (Aggregate, Star Schema, Merge)
       v
[Databricks: Gold Layer] 
    - Fact & Dimension Tables
    - Business-Ready Aggregates
       |
       v
[BI & Analytics]
    - Databricks SQL Dashboards
    - AI Genie
```

## 3. Data Flow
The data pipeline processes supply chain and sales data through three rigorous stages:

1.  **Ingestion (Bronze):** Raw CSV files (Customers, Products, Orders) are read from AWS S3 Landing buckets. Two metadata columns (`read_timestamp`, `file_name`) are added for lineage. Data is written as external Delta tables with Change Data Feed (CDF) enabled.
2.  **Refinement (Silver):**
    *   **Cleaning:** Removal of duplicate records, trimming whitespace, and fixing fat-finger errors (e.g., standardizing "Bangalore" vs. "Bengaluru").
    *   **Normalization:** Splitting product variants (e.g., "60g bar") from names and standardizing date formats.
    *   **Transformation:** Generating surrogate keys (SHA hashing) to replace unreliable legacy IDs.
3.  **Aggregation (Gold):**
    *   Data is modeled into a **Star Schema** with Fact tables (Orders) and Dimensions (Customers, Products).
    *   Child company data is merged into the parent company's existing Gold tables using `UPSERT` logic to ensure idempotency.

## 4. Technologies Used
*   **Platform:** Databricks (Free Edition/Standard).
*   **Governance:** Unity Catalog (Catalog: `FMCG`, Schemas: `Bronze`, `Silver`, `Gold`).
*   **Storage:** AWS S3 (Landing, Processed, and Delta Lake storage).
*   **Compute:** PySpark for ETL transformations.
*   **Data Format:** Delta Lake (Open source storage layer).
*   **Orchestration:** Databricks Workflows (Jobs).
*   **Language:** Python (PySpark) and SQL.

## 5. Usage of External Tables & Delta Lake
This project utilizes **External Tables** registered in Unity Catalog. This design decouples the compute (Databricks) from the storage (AWS S3), allowing data to persist in user-managed S3 buckets even if the Databricks workspace is modified.

*   **Delta Lake Configuration:** All tables are written in `DELTA` format to support ACID transactions.
*   **Change Data Feed (CDF):** CDF is enabled on tables (`delta.enableChangeDataFeed = true`) to track row-level changes (inserts, updates, deletes) efficiently, facilitating downstream incremental processing and audit trails.
*   **Unity Catalog:** Acts as the central governance layer, managing permissions and lineage across the external S3 locations.

## 6. Setup & Prerequisites
1.  **AWS Configuration:**
    *   Create an S3 bucket (e.g., `sports-bar-dp`) with folders: `full_load`, `incremental_load`, and `landing`.
    *   Configure AWS permissions/IAM roles for Databricks access.
2.  **Databricks Configuration:**
    *   Create a **Storage Credential** and **External Location** in Databricks pointing to the S3 bucket.
    *   Initialize the Unity Catalog structure:
        ```sql
        CREATE CATALOG IF NOT EXISTS fmcg;
        CREATE SCHEMA IF NOT EXISTS fmcg.bronze;
        CREATE SCHEMA IF NOT EXISTS fmcg.silver;
        CREATE SCHEMA IF NOT EXISTS fmcg.gold;
        ```
3.  **Data Loading:** Upload the provided "Full Load" CSV datasets to the S3 bucket.

## 7. How to Run the Notebooks
The pipeline is modularized. Notebooks should be executed in the following order (or via the configured Databricks Job):

1.  **Setup:** Run `setup_catalogs_and_tables` to initialize the environment.
2.  **Dimensions Processing:** Run `customer_data_processing` and `product_data_processing` to build dimension tables.
3.  **Fact Processing:** Run `fact_orders_full_load` for the historical backfill.
4.  **Incremental Loading:** For daily updates, place new files in the S3 `landing` folder and execute `incremental_load_orders`. This handles the "Merge/Upsert" logic.

*Note: Use the Databricks Widgets at the top of notebooks to define environment variables (Catalog Name, Bucket Paths) dynamically.*

## 8. Folder Structure
The project code is organized within the Databricks Workspace as follows:

```text
consolidated_pipeline/
├── setup/
│   ├── setup_catalogs.ipynb       # SQL scripts for Unity Catalog init
│   └── utilities.ipynb            # Common config (schema names, paths)
├── dimension_data_processing/
│   ├── customer_processing.ipynb  # Bronze->Silver->Gold for Customers
│   ├── product_processing.ipynb   # Regex parsing & standardization
│   └── price_processing.ipynb     # Handling currency & negative values
└── fact_data_processing/
    ├── 1_full_load.ipynb          # Historical batch processing
    └── 2_incremental_load.ipynb   # Daily incremental CDC processing
```

## 9. Key Design Decisions

*   **Why External Tables?**
    Using explicit S3 paths allows full control over the data retention policy and enables access by other tools outside Databricks if necessary. It prevents data loss during workspace lifecycle changes.

*   **Why Delta Lake?**
    Standard CSVs lack transaction support. Delta Lake provides reliability (ACID), enforces schema constraints (preventing bad data from corrupting downstream analytics), and enables "Time Travel" for debugging historical states.

*   **Surrogate Keys:**
    The legacy system used unstable integer IDs. We generated SHA-based surrogate keys (`product_code`) to ensure uniqueness across the merged entities (Parent and Child companies).

## 10. Sample Code Snippets

**Reading Raw Data with Metadata:**
```python
# Reading CSV with schema inference and adding lineage columns
df = spark.read.format("csv") \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .load(base_path) \
    .withColumn("read_timestamp", current_timestamp()) \
    .withColumn("file_name", input_file_name())
```

**Writing to Bronze with CDC:**
```python
# Writing as an External Delta Table with Change Data Feed enabled
df.write.format("delta") \
    .mode("overwrite") \
    .option("path", "s3://my-bucket/bronze/customers") \
    .option("enableChangeDataFeed", "true") \
    .saveAsTable("fmcg.bronze.customers")
```

**Gold Layer Upsert (Merge):**
```python
# Merging child data into the parent Gold table
deltaTable = DeltaTable.forName(spark, "fmcg.gold.fact_orders")

deltaTable.alias("target").merge(
    source = df_staging.alias("source"),
    condition = "target.order_id = source.order_id"
).whenMatchedUpdateAll() \
 .whenNotMatchedInsertAll() \
 .execute()
```

## 11. Future Improvements
*   **Automated Ingestion:** Currently, parent company data is assumed to be present. A future enhancement would automate the ingestion of the parent's OLTP data.
*   **Data Quality Framework:** Integrate **Great Expectations** to automate data quality checks (e.g., verifying no negative prices) before promoting data to Silver.
*   **CI/CD:** Implement a CI/CD pipeline using Databricks Asset Bundles (DABs) for version control and deployment.
*   **Streaming:** Convert the `incremental_load` to use Databricks Auto Loader for near real-time ingestion instead of batch scheduling.

---
*Based on the "End to End Data Engineering Project using Databricks" curriculum.*
