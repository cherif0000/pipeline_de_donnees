import pandas as pd

from src.transform import RANGES, check_quality


def make_df(rows=24):
    data = {"city": ["Dakar"] * rows,
            "time": pd.date_range("2026-11-03", periods=rows, freq="h")}
    for col in RANGES:
        data[col] = [20.0] * rows
    return pd.DataFrame(data)


def test_clean_data_has_no_problem():
    assert check_quality(make_df()) == []


def test_missing_rows_are_detected():
    assert any("23 lignes" in p for p in check_quality(make_df(23)))


def test_null_value_is_detected():
    df = make_df()
    df.loc[0, "pm2_5"] = None
    assert any("manquantes" in p and "pm2_5" in p for p in check_quality(df))


def test_out_of_range_value_is_detected():
    df = make_df()
    df.loc[0, "temperature_2m"] = 99
    assert any("hors plage" in p for p in check_quality(df))


def test_duplicates_are_detected():
    df = pd.concat([make_df(), make_df().iloc[[0]]])
    assert any("doublons" in p for p in check_quality(df))