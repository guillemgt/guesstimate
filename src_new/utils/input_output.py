import inspect
import os

def output_and_log_files(output_file: str | None, log_file: str | None):
    name_of_caller_file = None

    # Get the current frame
    frame = inspect.currentframe()
    try:
        # Get the frame of the caller (the file that called this function)
        caller_frame = frame.f_back
        caller_file = caller_frame.f_code.co_filename
        # Extract the base name of the file without extension
        name_of_caller_file =  os.path.splitext(os.path.basename(caller_file))[0]
    finally:
        # Explicitly delete the frame to prevent reference cycles
        del frame

    assert name_of_caller_file is not None

    if output_file is None:
        output_file = "data/pipeline/" + name_of_caller_file + ".json"
    if log_file is None:
        log_file = "data/pipeline/logs/" + name_of_caller_file + ".log"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    return output_file, log_file