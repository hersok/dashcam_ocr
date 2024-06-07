import pytest
from scripts.ocr_functions import directory_to_dataframe
from scripts.map_functions import clean_dataframe
import polars as pl

def test_dataframe():
    test_df = directory_to_dataframe("frames/010979F/")
    true_data = [
        [0, '08-04-2024 11:28:08', 30.759489, -97.730664, 72, 'MPH'],
        [3, '08-04-2024 11:28:11', 30.75957, -97.731689, 73, 'MPH'],
        [6, '08-04-2024 11:28:14', 30.759644, -97.732731, 74, 'MPH']
    ]
    true_df = pl.DataFrame(
        true_data,
        schema=[
            ('frame_index', pl.Int64),
            ('timestamp', pl.Utf8),
            ('latitude', pl.Float64),
            ('longitude', pl.Float64),
            ('speed', pl.Int64),
            ('speed_units', pl.Utf8)
        ]
    )

    assert test_df.frame_equal(true_df), "Error: The generated dataframe does not match the true values."


def test_filtering_df():
    df = pl.read_csv("output/dashcam.csv")
    filtered_df = clean_dataframe(df)
    # anomalous rows:
    # 45,08-04-2024 11:04:53,0.0,0.0,54,MPH
    # 99,08-04-2024 11:05:47,40.459477,-107.667269,71,MPH
    # 114,08-04-2024 11:06:02,30.4637,-97.66862,1000,MPH
    # 174,08-04-2024 11:07:02,0.0,0.0,69,MPH

    assert (df.height - filtered_df.height) == 4, "Error: The four anomalous rows were not filtered out."
