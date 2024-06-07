import os

import polars as pl
import folium as fl
import branca.colormap as cm
from scripts.ocr_functions import write_dataframe_to_file

def clean_dataframe(df: pl.DataFrame) -> pl.DataFrame:

    # reindex the dataframe:
    df = df.with_columns(pl.col("frame_index").diff().fill_null(0).alias("frame_delta"))
    interval = df.select(pl.col("frame_delta").mode()).to_series()[0]
    df = df.with_columns(pl.Series(name="new_index", values=range(0, interval * df.height, interval)))
    df = df.drop("frame_delta").drop("frame_index")

    df = df.filter(pl.col("latitude") != 0)
    df = df.filter(abs(pl.col("latitude")) <= 90)
    df = df.filter(abs(pl.col("longitude")) <= 180)

    # filter out extraneous lat, lon coords
    # the OCR operation interpreted some latitudes as 34.1 etc., which is out of the 30.4 to 31.1 range
    latitude_mean = df["latitude"].mean()
    latitude_std = df["latitude"].std()
    std_threshold = 2
    speed_std_threshold = 3
    longitude_mean = df["longitude"].mean()
    longitude_std = df["longitude"].std()
    speed_mean = df["speed"].mean()
    speed_std = df["speed"].std()
    df = df.filter(
        (abs(df["latitude"]) >= abs(latitude_mean) - std_threshold * latitude_std) &
        (abs(df["latitude"]) <= abs(latitude_mean) + std_threshold * latitude_std)
    )
    df = df.filter(
        (abs(df["longitude"]) >= abs(longitude_mean) - std_threshold * longitude_std) &
        (abs(df["longitude"]) <= abs(longitude_mean) + std_threshold * longitude_std)
    )
    df = df.filter(
        (abs(df["speed"]) >= abs(speed_mean) - speed_std_threshold * speed_std) &
        (abs(df["speed"]) <= abs(speed_mean) + speed_std_threshold * speed_std)
    )

    # A second geocoord filtering method
    # This filtering stage keeps track of the differences between coordinates
    # If a coordinate varies drastically from its predecessor, it gets filtered out.
    df = df.with_columns(pl.col("latitude").diff().fill_null(0).alias("lat_delta"))
    df = df.with_columns(pl.col("longitude").diff().fill_null(0).alias("lon_delta"))
    latitude_diff_mean = df["lat_delta"].mean()
    latitude_diff_std = df["lat_delta"].std()
    longitude_diff_mean = df["lon_delta"].mean()
    longitude_diff_std = df["lon_delta"].std()
    # the multiplier was added in to not penalize small sample sizes: (1 + 100 / df.height)
    df = df.filter(
        (abs(df["lat_delta"]) >= abs(latitude_diff_mean) - std_threshold * (1 + 100 / df.height) * latitude_diff_std) &
        (abs(df["lat_delta"]) <= abs(latitude_diff_mean) + std_threshold * (1 + 100 / df.height) * latitude_diff_std)
    )
    df = df.filter(
        (abs(df["lon_delta"]) >= abs(longitude_diff_mean) - std_threshold * (1 + 100 / df.height) * longitude_diff_std) &
        (abs(df["lon_delta"]) <= abs(longitude_diff_mean) + std_threshold * (1 + 100 / df.height) * longitude_diff_std)
    )

    # save the dataframe to file
    write_dataframe_to_file(df, "../output/", "filtered_dashcam.csv")

    # return the dataframe
    return df

def create_map(df: pl.DataFrame, output_dir = "output/"):

    # Extract data for Folium
    latitudes = df['latitude'].to_list()
    longitudes = df['longitude'].to_list()
    speeds = df['speed'].to_list()
    average_latitude = df.select(pl.col("latitude").mean()).to_series()[0]
    average_longitude = df.select(pl.col("longitude").mean()).to_series()[0]

    # Initialize a Folium map
    m = fl.Map(
        location=[average_latitude, average_longitude],
        zoom_start=10
    )

    # Create a colormap
    colormap = cm.LinearColormap(
        colors=['red', 'yellow', 'green'],
        vmin=min(speeds),
        vmax=max(speeds)
    )

    # Add PolyLine with different colors based on speed
    points = list(zip(latitudes, longitudes, speeds))
    for i in range(len(points) - 1):
        fl.PolyLine(
            locations=[(points[i][0], points[i][1]), (points[i + 1][0], points[i + 1][1])],
            color=colormap(points[i + 1][2]),
            weight=5
        ).add_to(m)

    # Apply colormap to the map
    colormap.add_to(m)

    # Add map title
    title_html = '''
                     <div style="position: fixed; 
                     bottom: 50px; left: 50px; width: 500px; height: 50px; 
                     background-color: #85D4FF; z-index:9999; font-size:24px;
                     font-weight: bold;
                     ">&nbsp;Car Drive from Austin, TX to Lampasas, TX</div>
                     '''
    m.get_root().html.add_child(fl.Element(title_html))

    # Check that directory exists
    if not os.path.exists(f"{output_dir.rstrip('/')}"):
        os.makedirs(f"{output_dir.rstrip('/')}")
    m.save(f"{output_dir.rstrip('/')}/map.html")



if __name__ == "__main__":
    df = pl.read_csv("output/dashcam.csv")
    df = clean_dataframe(df)
    create_map(df, "../output/")
