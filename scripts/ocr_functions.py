import re
import cv2
import pytesseract
import numpy as np
import os
import polars as pl

def image_to_text(file_name: str) -> str:
    """
    This function converts an image into text using Tesseract OCR's built-in methods.
    The image is pre-processed using grayscaling, eroding, dilating, blurring, and segmenting.
    The image pre-processing pipeline is inspired by: https://stackoverflow.com/a/50762612
    :param file_name: a relative path link to the image file
    :return: a string representing the OCR image-to-text output
    """
    # open the image
    image = cv2.imread(file_name)
    assert image is not None, "Could not open image"

    # Begin the pre-processing pipeline

    # convert image to grayscale to reduce computational complexity
    grayscale_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    kernel = np.ones((1, 1), np.uint8)

    # smooth out the image
    img = cv2.dilate(grayscale_img, kernel, iterations=1)

    # remove small noise objects
    img = cv2.erode(img, kernel, iterations=1)

    # Segment the text from the background using OTSU thresholding
    new_img = cv2.threshold(cv2.medianBlur(img, 3), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Use pytesseract to convert the pre-processed image into text
    # tesseract installed on Windows from https://github.com/UB-Mannheim/tesseract/wiki
    # Then add to PATH --> %UserProfile%\AppData\Local\Programs\Tesseract-OCR
    extracted_text = pytesseract.image_to_string(new_img)

    # resource cleanup
    cv2.destroyAllWindows()

    return extracted_text

def image_directory_to_dict(input_dir: str):
    """
    This function converts a given input directory of gps, speed, or time images into a python dictionary.
    The dictionary structure differs for gps, speed, and time information, but frame_index is the key for all outputs.
    :param input_dir:
    :return:
    """
    # Check that directory exists
    input_dir = input_dir.rstrip('/')
    assert os.path.exists(f"{input_dir}"), "Directory does not exist"

    regex_suffix_pattern = re.compile(r'\D*(\d+)\D*')
    # Example: frame_1.jpg = frame_(1).jpg
    regex_image_pattern = re.compile(r'\.(jpg|jpeg|png)$', re.IGNORECASE)
    regex_directory_pattern = re.compile(r'\.\./(frames)/(\S*)/(\D*)')
    # Example: ../frames/010243F/time = ../(frames)/(010243F)/(time)

    # list all files in the directory:
    all_files = os.listdir(input_dir)

    # find the subset of files that are images:
    image_files = [f for f in all_files if regex_image_pattern.search(f)]

    assert len(image_files) > 0, "Provided directory does not contain any images"

    # sort the image files in order of frame precedence
    # cast the suffixes to int so that they are sortable
    image_files.sort(key=lambda x: int(regex_suffix_pattern.search(x).group(1)))
    data_type = regex_directory_pattern.search(input_dir).group(3)

    frame_dict = {}
    for image_name in image_files:
        numerical_suffix = int(regex_suffix_pattern.search(image_name).group(1))

        relative_path = f"{input_dir}/{image_name}"
        print(f"Processed {relative_path}")

        img = cv2.imread(relative_path)
        assert img is not None, "Unable to open the provided image"

        extracted_text = image_to_text(relative_path)

        # switch statement
        if data_type == "gps":
            frame_dict[numerical_suffix] = {data_type: text_to_coordinates(extracted_text)}
        elif data_type == "speed":
            frame_dict[numerical_suffix] = {data_type: text_to_speed(extracted_text)}
        elif data_type == "time":
            frame_dict[numerical_suffix] = {data_type: text_to_timestamp(extracted_text)}
        else:
            print("Warning: The provided directory is not recognized as a datatype")
            frame_dict[numerical_suffix] = {'Error': 'Unrecognized Datatype'}

    return frame_dict

def text_to_coordinates(coord_string: str) -> dict[str, float]:
    """
    This function takes a potentially imperfect GPS coord input and outputs a tuple of floats representing the coords.
    The output order is lon, lat. North and East are positive, while South and West are negative.
    :param coord_string:
    :return: tuple[float, float]
    """
    # N40.426786 W97 .665820 = (N)(40)(.)(426786) (W)(97)( .)(665820)
    regex_coord_pattern = re.compile(r'([NS])\D*(\d+)(\s*\.\s*)(\d+)\s*([EW])\D*(\d+)(\s*\.\s*)(\d+)')
    regex_match = regex_coord_pattern.search(coord_string)
    if not regex_match:
        return {'latitude': 0.0, 'longitude': 0.0}
    lat_dir, lat_whole_number, lat_decimal, lat_float_number, lon_dir, lon_whole_number, lon_decimal, lon_float_number = regex_match.groups()
    latitude_coord = float(lat_whole_number + "." + lat_float_number) * (1 if lat_dir == 'N' else -1)
    longitude_coord = float(lon_whole_number + "." + lon_float_number) * (1 if lon_dir == 'E' else -1)

    gps_dict = {'latitude': latitude_coord, 'longitude': longitude_coord}

    return gps_dict

def text_to_timestamp(timestamp_string: str) -> str:
    """
    This function takes a potentially imperfect timestamp and outputs a formatted timestamp.
    :param timestamp_string:
    :return: str
    """
    # Example: "08-04-2024 11:  04 :13" = (08)-(04)-(2024) (11):  (04) :(13) = (08)-(04)-(2024) (11):(04):(13)
    regex_timestamp_pattern = re.compile(r'(\d{2})\D*(\d{2})\D*(\d{4})\s*(\d{2})\D*(\d{2})\s*\D*(\d{2})')
    regex_match = regex_timestamp_pattern.search(timestamp_string)
    if not regex_match:
        return timestamp_string
    day, month, year, hour, minute, second = regex_match.groups()
    return f"{day}-{month}-{year} {hour}:{minute}:{second}"

def text_to_speed(speed_string: str) -> dict[str, int | str]:
    """
    This function takes a potentially imperfect speed and outputs a formatted speed.
    The regex pattern checks for an up to 3 digit speed and a UNIT string.
    The output is an (int, str) tuple. e.g. "0 MPH" = (0, 'MPH')
    :param speed_string:
    :return:
    """
    # Example: 8   MPH = (8)   (MPH)
    regex_speed_pattern = re.compile(r'(\d{1,3})\s*([A-Za-z]{3,}.*)')
    regex_match = regex_speed_pattern.search(speed_string)
    if not regex_match:
        return {"speed": 0, "speed_units": "MPH"}
    speed_str, speed_units = regex_match.groups()

    speed_dict = {"speed": int(speed_str), "speed_units": speed_units}

    return speed_dict

def dict_to_dataframe(time_dict: dict, gps_dict: dict, speed_dict: dict) -> pl.DataFrame:
    """
    This function takes an input of three dictionaries and returns a polars DataFrame.
    :param time_dict:
    :param gps_dict:
    :param speed_dict:
    :return: polars DataFrame
    """

    # time_dict = frame_index = {'time': '22-09-2023 10:50:11'}
    time_df = pl.DataFrame(
        {
            'frame_index': list(time_dict.keys()),
            'timestamp': list(entry['time'] for entry in time_dict.values())
        }
    )

    # gps_dict = frame_index = {'gps': {'latitude': 30.426786, 'longitude': -97.66582}}
    gps_df = pl.DataFrame(
        {
            'frame_index': list(gps_dict.keys()),
            'latitude': list(entry['gps']['latitude'] for entry in gps_dict.values()),
            'longitude': list(entry['gps']['longitude'] for entry in gps_dict.values())
        }
    )

    # speed_dict = frame_index = {'speed': {'speed': 8, 'speed_units': 'MPH'}}
    speed_df = pl.DataFrame(
        {
            'frame_index': list(speed_dict.keys()),
            'speed': list(entry['speed']['speed'] for entry in speed_dict.values()),
            'speed_units': list(entry['speed']['speed_units'] for entry in speed_dict.values())
        }
    )

    joined_df = time_df.join(gps_df, on='frame_index').join(speed_df, on='frame_index')
    return joined_df

def directory_to_dataframe(input_dir: str) -> pl.DataFrame:
    """
    This function converts a single directory to a single DataFrame.
    :param input_dir:
    :return:
    """
    # Check that directory exists
    input_dir = input_dir.rstrip('/')
    assert os.path.exists(f"{input_dir}"), "Directory does not exist"

    time_dict = image_directory_to_dict(f"{input_dir}/time")
    gps_dict = image_directory_to_dict(f"{input_dir}/gps")
    speed_dict = image_directory_to_dict(f"{input_dir}/speed")

    return dict_to_dataframe(time_dict, gps_dict, speed_dict)

def all_directories_to_dataframe(input_dir: str) -> pl.DataFrame:
    """
    This function creates a DataFrame for each separate video directory. A single concatenated DataFrame is returned.
    :param input_dir:
    :return:
    """
    # Check that directory exists
    input_dir = input_dir.rstrip('/')
    assert os.path.exists(f"{input_dir}"), "Directory does not exist"

    subfolders = os.listdir(input_dir)
    assert len(subfolders) > 0, f"Error: there are no subfolders in directory: {input_dir}"
    print(subfolders)

    # create the first dataframe
    base_df = directory_to_dataframe(f"{input_dir}/{subfolders[0]}")

    for i in range(1, len(subfolders), 1):
        new_df = directory_to_dataframe(f"{input_dir}/{subfolders[i]}")
        base_df = base_df.vstack(new_df)

    return base_df

def write_dataframe_to_file(df: pl.DataFrame, output_dir = "output/", file_name = "dashcam.csv"):
    """
    This function saves a polars DataFrame to the specified directory as a CSV.
    :param df:
    :param output_dir:
    :param file_name:
    :return:
    """
    output_dir = output_dir.rstrip('/')
    if not os.path.exists(f"{output_dir.rstrip('/')}"):
        os.makedirs(f"{output_dir.rstrip('/')}")
    df.write_csv(f"{output_dir}/{file_name}")

if __name__ == "__main__":
    data_df = all_directories_to_dataframe("../frames/")
    write_dataframe_to_file(data_df, "../output/", "dashcam.csv")
    print(data_df)