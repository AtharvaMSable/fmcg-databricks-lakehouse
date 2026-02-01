# Databricks notebook source
# MAGIC %sql
# MAGIC
# MAGIC CREATE CATALOG IF NOT EXISTS fmcg;

# COMMAND ----------

# MAGIC %sql
# MAGIC USE CATALOG fmcg;

# COMMAND ----------

# MAGIC %md
# MAGIC Silver and Bronze schemas are exclusively for child company(Sportsbar)
# MAGIC whereas Gold schema will eventually contain data from both parent and child company 

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC CREATE SCHEMA IF NOT EXISTS fmcg.gold;
# MAGIC CREATE SCHEMA IF NOT EXISTS fmcg.silver;
# MAGIC CREATE SCHEMA IF NOT EXISTS fmcg.bronze;
# MAGIC