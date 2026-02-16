# src/csv_reasoner.py

import pandas as pd
import re
from src.logger import logger
from src.sqlite_store import SQLiteStore


COMPARISON_KEYWORDS = {
    "max": ["max", "maximum", "highest", "largest", "greatest", "peak"],
    "min": ["min", "minimum", "lowest", "smallest", "least"],
    "average": ["average", "mean", "avg"],
    "sum": ["total", "sum"],
    "count": ["count", "how many", "number of"],
}


def detect_numeric_intent(query: str):
    q = query.lower()
    for intent, words in COMPARISON_KEYWORDS.items():
        for w in words:
            if w in q:
                return intent
    return None


def clean_numeric_series(series: pd.Series):
    cleaned = (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def tokenize(text: str):
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def detect_relevant_column(query: str, df: pd.DataFrame):

    query_tokens = set(tokenize(query))
    numeric_columns = []

    for col in df.columns:
        cleaned = clean_numeric_series(df[col])
        if not cleaned.isna().all():
            numeric_columns.append(col)

    if not numeric_columns:
        return None

    best_column = None
    best_score = 0

    for col in numeric_columns:
        col_tokens = set(tokenize(col))

        score = len(query_tokens.intersection(col_tokens))

        for qt in query_tokens:
            if qt in col.lower():
                score += 1

        if col.lower() in ["id", "index"]:
            score = 0

        if score > best_score:
            best_score = score
            best_column = col

    if best_score >= 1:
        return best_column

    return None


def answer_csv_query(query: str, file_name: str):

    logger.info("Attempting structured CSV reasoning")

    store = SQLiteStore()
    df = store.load_dataframe(file_name)

    if df is None:
        return None

    query_lower = query.lower()

    # Dataset-level
    if any(word in query_lower for word in ["row", "rows", "record", "records"]):
        return f"The dataset contains {len(df)} rows."

    intent = detect_numeric_intent(query)
    if not intent:
        return None

    column = detect_relevant_column(query, df)
    if not column:
        return None

    try:
        numeric_series = clean_numeric_series(df[column])

        if numeric_series.isna().all():
            return None

        date_column = None
        for col in df.columns:
            lower = col.lower()
            if any(word in lower for word in ["date", "time", "day", "month", "year"]):
                date_column = col
                break

        if intent == "max":
            idx = numeric_series.idxmax()
            value = numeric_series.max()
            if date_column:
                return f"The highest value of '{column}' occurred on {df.loc[idx][date_column]} with a value of {value:.2f}."
            return f"The highest value of '{column}' is {value:.2f}."

        if intent == "min":
            idx = numeric_series.idxmin()
            value = numeric_series.min()
            if date_column:
                return f"The lowest value of '{column}' occurred on {df.loc[idx][date_column]} with a value of {value:.2f}."
            return f"The lowest value of '{column}' is {value:.2f}."

        if intent == "average":
            value = numeric_series.mean()
            return f"The average value of '{column}' is {value:.2f}."

        if intent == "sum":
            value = numeric_series.sum()
            return f"The total sum of '{column}' is {value:.2f}."

        if intent == "count":
            value = numeric_series.count()
            return f"The count of '{column}' is {value}."

        return None

    except Exception:
        logger.exception("CSV reasoning computation error")
        return None
