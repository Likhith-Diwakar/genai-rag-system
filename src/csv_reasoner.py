# src/csv_reasoner.py

import pandas as pd
from src.logger import logger


COMPARISON_KEYWORDS = {
    "max": ["max", "maximum", "highest", "largest", "greatest"],
    "min": ["min", "minimum", "lowest", "smallest", "least"],
    "average": ["average", "mean", "avg"],
    "sum": ["total", "sum"],
    "count": ["count", "how many", "number of"],
}


# ----------------------------------------------------------
# Detect numeric intent
# ----------------------------------------------------------
def detect_numeric_intent(query: str):
    q = query.lower()

    for intent, words in COMPARISON_KEYWORDS.items():
        for w in words:
            if w in q:
                return intent

    return None


# ----------------------------------------------------------
# Clean numeric values safely
# ----------------------------------------------------------
def clean_numeric_series(series: pd.Series):
    cleaned = (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


# ----------------------------------------------------------
# Detect relevant column dynamically
# ----------------------------------------------------------
def detect_relevant_column(query: str, df: pd.DataFrame):
    q = query.lower()

    # Exact column match
    for col in df.columns:
        if col.lower() in q:
            return col

    # Partial match
    for col in df.columns:
        if any(word in col.lower() for word in q.split()):
            return col

    # Fallback: first numeric column
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        return numeric_cols[0]

    return None


# ----------------------------------------------------------
# Structured CSV reasoning engine
# ----------------------------------------------------------
def answer_csv_query(query: str, csv_path: str):
    logger.info("Attempting structured CSV reasoning")

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        logger.exception("Failed to load CSV")
        return None

    intent = detect_numeric_intent(query)
    if not intent:
        return None

    column = detect_relevant_column(query, df)
    if not column or column not in df.columns:
        return None

    try:
        numeric_series = clean_numeric_series(df[column])
        df[column] = numeric_series

        if numeric_series.isna().all():
            return None

        # Detect date column automatically
        date_column = None
        for col in df.columns:
            if "date" in col.lower():
                date_column = col
                break

        # ---------------- MAX ----------------
        if intent == "max":
            idx = numeric_series.idxmax()
            value = numeric_series.max()
            row = df.loc[idx]

            if date_column:
                return (
                    f"The highest value of '{column}' occurred on "
                    f"{row[date_column]} with a value of {value:.2f}."
                )
            return f"The highest value of '{column}' is {value:.2f}."

        # ---------------- MIN ----------------
        elif intent == "min":
            idx = numeric_series.idxmin()
            value = numeric_series.min()
            row = df.loc[idx]

            if date_column:
                return (
                    f"The lowest value of '{column}' occurred on "
                    f"{row[date_column]} with a value of {value:.2f}."
                )
            return f"The lowest value of '{column}' is {value:.2f}."

        # ---------------- AVERAGE ----------------
        elif intent == "average":
            value = numeric_series.mean()
            return f"The average value of '{column}' is {value:.2f}."

        # ---------------- SUM ----------------
        elif intent == "sum":
            value = numeric_series.sum()
            return f"The total sum of '{column}' is {value:.2f}."

        # ---------------- COUNT ----------------
        elif intent == "count":
            value = numeric_series.count()
            return f"The count of '{column}' is {value}."

        return None

    except Exception:
        logger.exception("CSV reasoning computation error")
        return None
