import base64
import os
import json
import time
import numpy as np
import cv2
from PIL import Image
from pynput import mouse
import pyautogui


VALUE_RANGE = {
    "Exposure": (-5.0, 5.0),
    "Contrast": (-100, 100),
    "Highlights": (-100, 100),
    "Shadows": (-100, 100),
    "Whites": (-100, 100),
    "Blacks": (-100, 100),
    "Temp": (-100, 100),
    "Tint": (-100, 100),
    "Vibrance": (-100, 100),
    "Saturation": (-100, 100),
}


test_parameters_1 = {
        "Exposure": 0,
        "Contrast": 0,
        "Highlights": 0,
        "Shadows": 0,
        "Whites": 0,
        "Blacks": 0,
        "Temp": 0,
        "Tint": 0,
        "Vibrance": 0,
        "Saturation": 0,
    }

test_parameters_2 = {
    "Exposure": 3.0,
    "Contrast": 70,
    "Highlights": 70,
    "Shadows": 70,
    "Whites": 70,
    "Blacks": 70,
    "Temp": -70,
    "Tint": -70,
    "Vibrance": -70,
    "Saturation": -70,
}

test_parameters_3 = {
    "Exposure": -3.0,
    "Contrast": -70,
    "Highlights": -70,
    "Shadows": -70,
    "Whites": -70,
    "Blacks": -70,
    "Temp": 70,
    "Tint": 70,
    "Vibrance": 70,
    "Saturation": 70,
}


def get_GUI_preview_image(gui_config, screenshot=None, save_path='cropped_image.jpg', tolerance=10):
    """
    Crop the GUI area from screenshot and remove background border.

    Parameters:
        gui_config (dict): Configuration dictionary containing:
            - 'HIDPI': Scaling ratio
            - 'canva_topleft': [x, y] Top-left coordinates
            - 'canva_bottomright': [x, y] Bottom-right coordinates 
            - 'background_color': [R, G, B] Background color
        screenshot (PIL.Image): Optional PIL image. If None, take screenshot automatically.
        save_path (str): Path to save the cropped image.
        tolerance (int): Tolerance for background color.
    
    Returns:
        cropped_image (numpy.ndarray): Cropped image in OpenCV format.
    """
    # Take screenshot if none provided
    if screenshot is None:
        screenshot = pyautogui.screenshot()

    # Calculate crop area
    topleft = [coord * gui_config['HIDPI'] for coord in gui_config['canva_topleft']]
    bottomright = [coord * gui_config['HIDPI'] for coord in gui_config['canva_bottomright']]
    crop_area = (topleft[0], topleft[1], bottomright[0], bottomright[1])

    # Crop the image region
    cropped_image_pil = screenshot.crop(crop_area)
    cv2_image = cv2.cvtColor(np.array(cropped_image_pil), cv2.COLOR_RGB2BGR)

    # Remove background border
    lower_bound = np.array([c - tolerance for c in gui_config['background_color']], dtype=np.uint8)
    upper_bound = np.array([c + tolerance for c in gui_config['background_color']], dtype=np.uint8)
    mask = cv2.inRange(cv2_image, lower_bound, upper_bound)

    # Find bounding box of non-background area
    coords = cv2.findNonZero(255 - mask)
    x, y, w, h = cv2.boundingRect(coords)
    cropped_image = cv2_image[y:y+h, x:x+w]

    short_edge_target = 512

    h, w = cropped_image.shape[:2]
    if h < w: 
        scale = short_edge_target / h
    else: 
        scale = short_edge_target / w
    new_width = int(w * scale)
    new_height = int(h * scale)

    resized_image = cv2.resize(cropped_image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(save_path, resized_image)


def get_GUI_histo_image(gui_config, screenshot=None, save_path='cropped_histo.jpg', tolerance=10):
    """
    Crop the specified GUI area from screenshot and remove background border.

    Parameters:
        gui_config (dict): Configuration dictionary containing:
            - 'HIDPI': Scaling ratio
            - 'canva_topleft': [x, y] Top-left coordinates
            - 'canva_bottomright': [x, y] Bottom-right coordinates
            - 'background_color': [R, G, B] Background color
        screenshot (PIL.Image): Optional PIL image. If None, take screenshot automatically.
        save_path (str): Path to save the cropped image.
        tolerance (int): Tolerance for background color.
    
    Returns:
        cropped_image (numpy.ndarray): Cropped image in OpenCV format.
    """
    # Take screenshot if none provided
    if screenshot is None:
        screenshot = pyautogui.screenshot()

    # Calculate crop area
    topleft = [coord * gui_config['HIDPI'] for coord in gui_config['histogram_topleft']]
    bottomright = [coord * gui_config['HIDPI'] for coord in gui_config['histogram_bottomright']]
    crop_area = (topleft[0], topleft[1], bottomright[0], bottomright[1])

    # Crop the image region
    cropped_image_pil = screenshot.crop(crop_area)
    cv2_image = cv2.cvtColor(np.array(cropped_image_pil), cv2.COLOR_RGB2BGR)

    # Save the image
    cv2.imwrite(save_path, cv2_image)


def set_slider_positions(target_parameters, GUI_config):
    """
    Automatically move the mouse and click on slider positions based on target parameters.

    Args:
        target_parameters (dict): Dictionary containing target values for sliders.
        GUI_config (dict): GUI configuration containing slider positions and HIDPI scaling.
    """
    for slider, value in target_parameters.items():
        if slider in GUI_config['adjustment_position']:
            x_pos, y_pos = get_slider_position(slider, value, GUI_config)
            # print(f"Setting {slider} to {value} at position ({x_pos}, {y_pos})")
            pyautogui.moveTo(x_pos, y_pos, duration=0.2)
            pyautogui.click()
            time.sleep(0.1)  # Small delay to ensure smooth execution


def get_slider_position(slider, value, GUI_config):
    """
    Get the screen coordinates for a slider based on its value.

    Args:
        slider (str): Name of the slider.
        value (float): Desired value for the slider.

    Returns:
        tuple: The x and y coordinates of the slider.
    """
    left, middle, right = GUI_config['adjustment_position'][slider]
    min_val, max_val = VALUE_RANGE[slider]

    if value <= 0:
        t = (value - min_val) / (0 - min_val)
        x_pos = left[0] + t * (middle[0] - left[0])
    else:
        t = (value - 0) / (max_val - 0)
        x_pos = middle[0] + t * (right[0] - middle[0])

    x_pos = x_pos / GUI_config['HIDPI']
    y_pos = middle[1] / GUI_config['HIDPI']
    return int(x_pos), int(y_pos)


def get_current_parameters(GUI_config):
    """
    Get the current values of sliders based on their positions on the screen.

    Args:
        slider_image (str): Path to the slider image.

    Returns:
        dict: A dictionary containing the current values of sliders.
    """
    detected_positions = list(pyautogui.locateAllOnScreen(GUI_config['controller_image_path'], confidence=0.95))
    current_values = {}

    for slider, positions in GUI_config['adjustment_position'].items():
        for pos in detected_positions:
            if abs((float(pos.top) + float(pos.height) / 2.0) - positions[0][1]) < 3:
                center_x = float(pos.left) + float(pos.width) / 2.0
                left, middle, right = positions
                min_val, max_val = VALUE_RANGE[slider]
    
                if center_x <= middle[0]:
                    t = (center_x - left[0]) / (middle[0] - left[0])
                    value = min_val + t * (0 - min_val)
                else:
                    t = (center_x - middle[0]) / (right[0] - middle[0])
                    value = 0 + t * (max_val - 0)
    
                current_values[slider] = int(value)
                break

    return current_values


def create_toolbox_config_template(button_image, HDPI, background_color, pannel_and_histogram_area, slider_positions):
    """
    Creates a Toolbox Config Template with the provided parameters.

    Args:
        button_image (str): Path to the button image.
        HDPI (int): High DPI scaling factor.
        pannel_and_histogram_area (dict): Coordinates for pannel and histogram areas.
        slider_positions (dict): Slider positions for adjustments.

    Returns:
        dict: A formatted toolbox configuration template.
    """
    toolbox_config_template = {
        "canva_topleft": pannel_and_histogram_area["canva_topleft"],
        "canva_bottomright": pannel_and_histogram_area["canva_bottomright"],
        "pannel_topleft": pannel_and_histogram_area["pannel_topleft"],
        "pannel_bottomright": pannel_and_histogram_area["pannel_bottomright"],
        "histogram_topleft": pannel_and_histogram_area["histogram_topleft"],
        "histogram_bottomright": pannel_and_histogram_area["histogram_bottomright"],
        "controller_image_path": button_image,
        "adjustment_position": slider_positions,
        "HIDPI": HDPI,
        "background_color": background_color
    }

    return toolbox_config_template


def record_slider_positions(slider_image):
    """
    Records the positions of sliders in the middle, far left, and far right positions.
    Args:
        slider_image (str): Path to the slider image.
    Returns:
        dict: A dictionary containing the positions of each slider.
    """
    sliders = [
        "Exposure", "Contrast", "Highlights", "Shadows",
        "Whites", "Blacks", "Temp", "Tint",
        "Vibrance", "Saturation"
    ]

    slider_positions = {slider: [None, None, None] for slider in sliders}

    print("Ensure all sliders are in the middle position.")
    input("Press Enter after confirming all sliders are set to the middle position...")

    print("Recording middle positions...")
    for i, slider in enumerate(sliders):
        all_positions = list(pyautogui.locateAllOnScreen(slider_image))
        if all_positions:
            slider_positions[slider][1] = (int(all_positions[i].left + all_positions[i].width / 2), int(all_positions[i].top + all_positions[i].height / 2))

    print("Move all sliders to the far left position.")
    input("Press Enter after adjusting all sliders to the far left...")

    print("Recording far left positions...")
    for i, slider in enumerate(sliders):
        all_positions = list(pyautogui.locateAllOnScreen(slider_image))
        if all_positions:
            slider_positions[slider][0] = (int(all_positions[i].left + all_positions[i].width / 2), int(all_positions[i].top + all_positions[i].height / 2))

    print("Move all sliders to the far right position.")
    input("Press Enter after adjusting all sliders to the far right...")

    print("Recording far right positions...")
    for i, slider in enumerate(sliders):
        all_positions = list(pyautogui.locateAllOnScreen(slider_image))
        if all_positions:
            slider_positions[slider][2] = (int(all_positions[i].left + all_positions[i].width / 2), int(all_positions[i].top + all_positions[i].height / 2))

    print("Recording complete. Final slider positions:")
    for slider, positions in slider_positions.items():
        print(f"{slider}: {positions}")

    return slider_positions


def set_calibration_points():
    """
    Guide users to right-click on 4 points on the screen, corresponding to:
    - canva_topleft
    - canva_bottomright
    - pannel_topleft
    - pannel_bottomright
    - histogram_topleft
    - histogram_bottomright

    Returns a dictionary containing these coordinates.
    """
    points = {
        "canva_topleft": None,
        "canva_bottomright": None,
        "pannel_topleft": None,
        "pannel_bottomright": None,
        "histogram_topleft": None,
        "histogram_bottomright": None
    }

    point_names = list(points.keys())
    index = 0

    print("Please right-click on the following positions on the screen in order:")
    for name in point_names:
        print(f" - {name}")

    def on_click(x, y, button, pressed):
        nonlocal index
        if pressed and button == mouse.Button.right:
            # Save current click position with rounded coordinates
            points[point_names[index]] = (round(x), round(y))
            print(f"Recorded {point_names[index]}: {round(x), round(y)}")
            index += 1

            # Check if all points have been recorded
            if index >= len(point_names):
                print("All points have been recorded!")
                return False  # Stop listener

    # Start mouse listener
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()

    print("Final recorded points:")

    return points
