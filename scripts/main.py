import ocr_functions as ocr
import map_functions as map
import video_functions as vid
import polars as pl

if __name__ == '__main__':
    # extract video frames
    vid.directory_frame_extractor("../videos/", 3, 25, 0.5)

    # perform OCR on frame regions
    data_df = ocr.all_directories_to_dataframe("../frames/")
    ocr.write_dataframe_to_file(data_df, "../output/", "dashcam.csv")
    print(data_df)

    # create the map
    df = pl.read_csv("output/dashcam.csv")
    df = map.clean_dataframe(df)
    map.create_map(df, "../output/")
