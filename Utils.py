import base64
import os
import json


def base64_encode_image(image_path):
    """
    Encode an image file to a Base64 string.

    Parameters:
    image_path (str): The path to the image file.

    Returns:
    str: The encoded Base64 string.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

