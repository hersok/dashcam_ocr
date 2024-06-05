import cv2
import os
import re

def frame_extractor(file_name: str, time_offset: float, x: int, y: int, width: int, height: int, frame_type: str, output_dir = "frames/"):
    """
    This function saves a frame for a particular region of interest
    for the specified time interval.
    The files are saved into the /frames/ directory.
    """
    print(f"Your input was {file_name}")

    cap = cv2.VideoCapture(file_name)

    assert cap.isOpened(), "Could not open the specified video file"

    # jump to the specified timestamp
    cap.set(cv2.CAP_PROP_POS_MSEC, time_offset * 1000)

    ret, frame = cap.read()
    assert ret, "The frame at the specified timestamp did not open correctly"

    extracted_region = frame[y:y + height, x:x + width]

    # This assumes a Viofo standard filename from the Viofo A129 Plus
    regex_pattern = r'_(.*?)\.MP4'
    parent_folder = re.search(regex_pattern, file_name).group(1)

    if not os.path.exists(f"{output_dir.rstrip('/')}/{parent_folder}/{frame_type}"):
        os.makedirs(f"{output_dir.rstrip('/')}/{parent_folder}/{frame_type}")

    output_path = f"{output_dir.rstrip('/')}/{parent_folder}/{frame_type}/frame_{time_offset}.jpg"

    cv2.imwrite(output_path, extracted_region)
    print(f"Image saved to {output_path}")

    # resource cleanup
    cap.release()

def frame_extractor_loop(file_name: str, frequency: int, x: int, y: int, width: int, height: int, frame_type: str):
    """
    This function loops over a given input video and saves frames of the region of interest at the specified frequency.
    :param file_name:   complete path of video file
    :param frequency:   number of seconds between frame extracts
    :param x:           ROI x-coordinate
    :param y:           ROI y-coordinate
    :param width:       ROI width
    :param height:      ROI height
    :param frame_type:  the type of content extracted e.g. "gps", "timestamp", "speed"
    """
    cap = cv2.VideoCapture(file_name)

    assert cap.isOpened(), "Could not open the specified video file"

    # calculate the length of the video
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    length_in_seconds = int(total_frames / frame_rate)

    cap.release()

    # loop through video
    for i in range(0, length_in_seconds, frequency):
        frame_extractor(file_name, i, x, y, width, height, frame_type, "frames")


def region_of_interest_finder(file_name: str, time_offset: float, screen_size_ratio: float, selection_type: str):
    """
    This function opens a scaled window with the video frame at the specified timeframe for the input file.
    file_name:          the name of the video file
    time_offset:        time offset, in seconds. Floating point values accepted
    screen_size_ratio:  a number between 0 and 1 that scales the video...
                        so that it fits on the screen when you select the ROI.
    """

    assert 0 < screen_size_ratio <= 1, "The screen size ratio is invalid"

    print(f"The filename is {file_name}")
    cap = cv2.VideoCapture(file_name)

    assert cap.isOpened(), "Could not open the specified video file"

    # jump to the specified timestamp
    cap.set(cv2.CAP_PROP_POS_MSEC, time_offset * 1000)

    ret, frame = cap.read()
    assert ret, "The frame at the specified timestamp did not open correctly"

    # Get the dimensions of the frame
    f_height, f_width = frame.shape[:2]
    scaled_width = int(f_width * screen_size_ratio)
    scaled_height = int(f_height * screen_size_ratio)

    resized_frame = cv2.resize(frame, (scaled_width, scaled_height))
    # Get the dimensions of the frame
    f_height, f_width = resized_frame.shape[:2]
    # Print the dimensions
    print("Resized frame dimensions (f_width x f_height):", f_width, "x", f_height)

    roi = cv2.selectROI(f"Please draw a bounding box around the {selection_type} element", resized_frame)

    # since we scaled the frame to make it fit, we have to scale back the coords
    x = int(roi[0] * (1 / screen_size_ratio))
    y = int(roi[1] * (1 / screen_size_ratio))
    width = int(roi[2] * (1 / screen_size_ratio))
    height = int(roi[3] * (1 / screen_size_ratio))

    # resource cleanup
    cap.release()
    cv2.destroyAllWindows()

    return (x, y, width, height)

def directory_frame_extractor(input_dir: str, frequency: int, time_offset = 25, screen_size_ratio = 0.5):

    """
    This function converts a videos directory into a directory of extracted frames.
        Each frame directory is titled with the video number suffix.
        Each frame directory has 3 subdirs: gps, speed, time.
        This function requires the user to specify the region of interest in the video frame
    :param input_dir: an input directory containing the entirety of dashcam videos for a given trip
    :param time_offset: a time offset for displaying the frame to select a ROI. It defaults to 25 seconds b/c ...
                        ... the GPS signals take about that long to initialize after starting the car.
    :param screen_size_ratio: change the size of the frame window. Ratio of 0.5 if for a 2560x1440 video and screen size
    :param frequency: in physics terms, it should be called the period, not frequency. # of seconds between extracts.
    :return: Creates 3 child directories for each video file under the /frames/ directory
    """

    input_dir = input_dir.rstrip('/')
    assert os.path.exists(f"{input_dir}"), "Directory does not exist"

    files = os.listdir(input_dir)
    assert len(files) > 0, "Error: directory is empty"
    print(files[0])

    # prompt user to select a GPS ROI
    # gps_roi = (x, y, width, height)
    gps_roi = region_of_interest_finder(f"{input_dir}/{files[0]}", time_offset, screen_size_ratio, "gps")

    # prompt user to select a speed ROI
    speed_roi = region_of_interest_finder(f"{input_dir}/{files[0]}", time_offset, screen_size_ratio, "speed")

    # prompt user to select a time ROI
    time_roi = region_of_interest_finder(f"{input_dir}/{files[0]}", time_offset, screen_size_ratio, "time")

    for video_name in files:
        frame_extractor_loop(f"{input_dir}/{video_name}", frequency, gps_roi[0], gps_roi[1], gps_roi[2], gps_roi[3], "gps")
        frame_extractor_loop(f"{input_dir}/{video_name}", frequency, speed_roi[0], speed_roi[1], speed_roi[2], speed_roi[3], "speed")
        frame_extractor_loop(f"{input_dir}/{video_name}", frequency, time_roi[0], time_roi[1], time_roi[2], time_roi[3], "time")




if __name__ == "__main__":
    directory_frame_extractor("videos/", 3, 25, 0.5)

