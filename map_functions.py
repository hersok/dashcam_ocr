import os

import polars as pl
import folium as fl
import branca.colormap as cm
from ocr_functions import write_dataframe_to_file

def clean_dataframe(df: pl.DataFrame) -> pl.DataFrame:

    # reindex the dataframe:
    df = df.with_columns(pl.col("frame_index").diff().fill_null(0).alias("frame_delta"))
    interval = df.select(pl.col("frame_delta").mode()).to_series()[0]
    df = df.with_columns(pl.Series(name="new_index", values=range(0, interval * df.height, interval)))
    df = df.drop("frame_delta").drop("frame_index")

    # filter out extraneous lat, lon coords
    # the OCR operation interpreted some latitudes as 34.1 etc., which is out of the 30.4 to 31.1 range
    latitude_mean = df["latitude"].mean()
    latitude_std = df["latitude"].std()
    std_threshold = 0.5
    longitude_mean = df["longitude"].mean()
    longitude_std = df["longitude"].std()
    df = df.filter(
        (df["latitude"] >= latitude_mean - std_threshold * latitude_std) &
        (df["latitude"] <= latitude_mean + std_threshold * latitude_std)
    )
    df = df.filter(
        (df["longitude"] >= longitude_mean - std_threshold * longitude_std) &
        (df["longitude"] <= longitude_mean + std_threshold * longitude_std)
    )

    # save the dataframe to file
    write_dataframe_to_file(df, "output/", "filtered_dashcam.csv")

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
    create_map(df, "output/")
