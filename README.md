# 📄 DOI PDF Validator (ES/EN) — Streamlit Modular App

This repository contains the source code for a **modular Streamlit application** designed to analyze academic PDF documents and validate their bibliographic references using **Digital Object Identifiers (DOIs)**.

The application supports documents in **English and Spanish**, automatically detects and prioritizes the **References / Referencias / Bibliografía** section, validates DOI resolution via **doi.org**, and enriches results using the **Crossref API**.  
🚫 No web scraping is performed.

---

## 🎯 Objectives

- 📄 Extract text from academic PDF files  
- 📚 Detect and prioritize the references section (ES/EN)  
- 🔍 Identify DOIs using robust pattern matching  
- ✅ Validate whether each DOI resolves correctly  
- 🧪 Classify results into:
  - **valid** – resolves correctly  
  - **invalid** – does not exist or is malformed  
  - **unknown** – timeouts, rate limits, or server errors  
- 🧠 Enrich valid DOIs with titles and journals using Crossref  
- 🔎 Optionally infer missing DOIs from references without explicit identifiers  
- 📊 Provide interactive dashboards and exportable reports  

---

## 🧱 Project Structure

Allucinations---Project/
│
├── app.py
├── requirements.txt
├── README.md
│
└── src/
├── init.py
├── pdf_extract.py
├── references.py
├── doi_extract.py
├── doi_validate.py
├── metadata.py
└── reporting.py


---

## 🧩 Module Overview

### 🖥️ `app.py`
Main Streamlit application.  
Handles the user interface, parameter configuration, pipeline orchestration, visualizations, and exports.

### 📄 `pdf_extract.py`
Extracts text page by page from PDF documents using **pdfplumber** and applies text normalization.

### 📚 `references.py`
Detects and isolates the references section using multilingual headers such as:
- References  
- Referencias  
- Bibliografía  
- Referencias bibliográficas  

### 🔍 `doi_extract.py`
Extracts DOIs using multiple regex patterns, cleans artifacts, validates DOI format, removes duplicates, and assigns page numbers.

### 🌐 `doi_validate.py`
Validates DOIs by resolving them through `https://doi.org/{doi}`.  
Supports configurable **timeout**, **retries**, **concurrency**, and **caching**.  
Classifies results as **valid**, **invalid**, or **unknown**.

### 🧠 `metadata.py`
Uses the **Crossref API** to:
- Retrieve titles and journals for valid DOIs  
- Search for potential DOIs in references without explicit identifiers  

### 📊 `reporting.py`
Transforms results into Pandas DataFrames and generates exportable TXT reports.

---

## ⚙️ Configuration Parameters (UI)

- ⏱️ **Timeout (seconds):** Maximum waiting time per DOI request  
- 🔁 **Retries:** Number of retry attempts for transient failures  
- 🧵 **Threads:** Number of concurrent DOI validations  
- 📘 **Crossref options:**
  - Fetch title by DOI  
  - Search titles in references without DOI  
- 📏 **Max reference lines:** Limit for Crossref search input  

These parameters allow tuning **precision vs. performance**, similar to hyperparameters in data pipelines.

---

## ▶️ How to Run

### 1️⃣ Install dependencies and launch the application
```bash
pip install -r requirements.txt
streamlit run app.py
