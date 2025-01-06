import os
from typing import List, Callable
import numpy as np
from Levenshtein import distance

import pyautogui

import cv2
import matplotlib.pyplot as plt
from io import BytesIO
import ast

from PIL import Image, ImageEnhance, ExifTags
from ImageProcessing import *

from Utils import pretty_print_content
from Toolbox import tool_doc
from GUIUtils import *

def safe_color_str_to_list(input_str):
    try:
        # 使用 ast.literal_eval 解析字符串为 Python 数据类型
        parsed_list = ast.literal_eval(input_str)
        
        # 检查是否为列表且元素是数字
        if isinstance(parsed_list, list) and all(isinstance(x, (int, float)) for x in parsed_list):
            return parsed_list
        else:
            raise ValueError("Parsed object is not a list of numbers")
    except (ValueError, SyntaxError):
        print("Invalid input. Cannot convert to list.")
        return [0, 0, 0]


CURRENT_STATUS_TEMPLATE = {
    "adjustment_status": {
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
    },
    "color_adjustment_status": {
        "Red": [0, 0, 0],
        "Orange": [0, 0, 0],
        "Yellow": [0, 0, 0],
        "Green": [0, 0, 0],
        "Cyan": [0, 0, 0],
        "Blue": [0, 0, 0],
        "Purple": [0, 0, 0],
        "Magenta": [0, 0, 0],
    },
    "histogram_image": "/path/to/histogram.png",
    "current_image": "/path/to/current.png",
    "processing_image_step": 0,
}


class LightroomGUIToolBox:

    def __init__(self, config_dic, output_dir_name, debug=True, image_name='test_image', clip_history_messages=False):
        self.config = config_dic
        self.output_dir_path = output_dir_name
        self.image_name = image_name
        self.clip_history_messages = clip_history_messages

        if not os.path.exists(output_dir_name):
            os.makedirs(output_dir_name)
        elif debug:
            pass
        else:
            raise FileExistsError(f"The directory '{output_dir_name}' already exists.")

        self.current_status = CURRENT_STATUS_TEMPLATE
        self.global_step = 0  # Global step counter for the image processing
        self.image_paths = []  # List of image paths for OpenAI to view
        self.histogram_paths = []  # List of histogram paths
        self.processing_log = []  # Log of processing steps
        self.function_calls = []  # Record of function calls
        self._history_messages = []  # Record of conversation history
        self.processing_plan = []
        self.user_messages = []  # Record of messages back to user
        self.satisfactory_status = False
        self.log_file_path = os.path.join(self.output_dir_path, "processing_log.txt")

        self.get_current_GUI_status()
        self.user_message_figure()
        print(f"User messgae file path: {os.path.abspath(os.path.join(self.output_dir_path, 'user_messages.json'))}")

    def format_editing_params(self, params=None):
        """
        Format editing parameters as a string.
        - param `params`: Dictionary containing adjustment parameters.
        """
        if params is None:
            params = self.current_status    
        # Extract basic parameters and color adjustment status
        basic_params = params.get('adjustment_status', {})
        color_params = params.get('color_adjustment_status', {})

        # Format basic adjustment parameters
        result = []
        for key, value in basic_params.items():
            result.append(f"{key}: {value}")

        # Format color adjustment parameters
        color_adjustments = []
        for color, adjustments in color_params.items():
            if adjustments != [0, 0, 0]:  # Skip if all values are 0
                hue, saturation, luminance = adjustments
                color_str = f"{color} (Hue: {hue}, Saturation: {saturation}, Luminance: {luminance})"
                color_adjustments.append(color_str)

        # Join into final string
        if color_adjustments:
            result.append("Color Adjustments:")
            result.extend(color_adjustments)

        return "\n".join(result)

    def user_message_figure(self, image_path=None):
        if image_path is None:
            image_path = self.current_status["current_image"]
        self.user_messages.append({"role": "assistant", "content_type": "image", "content": image_path})
        self.save_user_messages()

    def save_user_messages(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.output_dir_path, "user_messages.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump({"user_message": self.user_messages}, file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Failed to save the message: {e}")
        
    def get_current_GUI_status(self):
        """
        Get the current status of the GUI
        """
        image_path = os.path.join(self.output_dir_path, f"{self.image_name}_{self.global_step}.jpg")
        histo_path = os.path.join(self.output_dir_path, f"{self.image_name}_{self.global_step}_histo.jpg")
        get_GUI_preview_image(self.config, save_path=image_path)
        get_GUI_histo_image(self.config, save_path=histo_path)

        self.image_paths.append(image_path)
        self.histogram_paths.append(histo_path)
        self.current_status["current_image"] = image_path
        self.current_status["histogram_image"] = histo_path
        self.current_status["processing_image_step"] = self.global_step

    def get_current_histo_image_path(self, image_number=1):
        """Return the path of the histogram of the most recently processed image
        This method is useful for retrieving the current state of the image after processing"""
        if image_number == 1:
            return self.histogram_paths[-1]
        else:
            return self.histogram_paths[-image_number]

    def get_current_image_path(self, image_number=1):
        """Return the path of the most recently processed image
        This method is useful for retrieving the current state of the image after processing"""
        if image_number == 1:
            return self.image_paths[-1]
        else:
            return self.image_paths[-image_number:]

    def set_current_status(self, status_dic):
        """
        Update the current status dictionary
        
        Args:
            status_dic (dict): Dictionary containing status items to update
        """
        for key, value in status_dic.items():
            if key in self.current_status:
                if isinstance(value, dict) and isinstance(self.current_status[key], dict):
                    # If nested dictionary, update recursively
                    self.current_status[key].update(value)
                else:
                    # Directly update the value
                    self.current_status[key] = value

    def set_satisfactory_status(self, status):
        self.satisfactory_status = status

    @staticmethod
    def get_tool_docs(tools: List[Callable]):
        tool_docs = []
        for func in tools:
            if callable(func) and hasattr(func, 'tool_doc'):
                tool_docs += [{"type": "function", "function": func.tool_doc[0]}] 
        return tool_docs

    def get_function_mapping(self):
        """
        Get a mapping of function names to their corresponding method names.
        This method is useful for retrieving the mapping of function names to their corresponding methods.
        """
        tool_docs = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'tool_doc'):
                tool_docs[attr.tool_doc[0]["name"]] = attr.__name__
        return tool_docs

    @tool_doc([
        {
            "name": "func_to_get_lightroom_adjustment",
            "description": (
                "A function of GPT that generates and builds a specific plan for retouching based on the analysis in the history.\n"
                "GPT should carefully select and arrange the available image retouching adjustments:\n"
                "Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Temp, Tint, Vibrance, Saturation. The initial value is 0.\n"
                "\n"
                "GPT also adjust specific colors. The available colors for adjustment are: 'Red', 'Orange', 'Yellow', 'Green', 'Cyan', 'Blue', 'Purple', 'Magenta'.\n"
                "For each color, you can adjust three dimensions: Hue (-100, 100), Saturation (-100, 100), and Luminance (-100, 100).\n"
                "Provide a list for each color adjustment, formatted as [Hue, Saturation, Luminance]. For example, [0, 20, -30] means the Hue remains unchanged, Saturation increases by 20, and Luminance decreases by 30.\n"
                "\n"
                "Avoid unnecessary color adjustments. Generally, adjust no more than two colors in the list of available colors. Don't make adjustments too drastically unless necessary.\n"
                "Try to avoid modifying the Hue unless it is necessary.\n"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "Exposure": {
                        "type": "number",
                        "description": ("Controls the intensity of exposure adjustment. Range: [-5, 5]: -5: Lowest exposure; 0: Original exposure; 5: Highest exposure\n")
                    },
                    "Contrast": {
                        "type": "integer",
                        "description": ("Controls the intensity of contrast adjustment. Range: [-100, 100]: -100: Lowest contrast; 0: Original contrast; 100: Highest contrast\n")
                    },
                    "Highlights": {
                        "type": "integer",
                        "description": ("Controls the intensity of highlights adjustment. Range: [-100, 100]: -100: Lowest highlights; 0: Original highlights; 100: Highest highlights\n")
                    },  
                    "Shadows": {
                        "type": "integer",
                        "description": ("Controls the intensity of shadows adjustment. Range: [-100, 100]: -100: Lowest shadows; 0: Original shadows; 100: Highest shadows\n")
                    },  
                    "Whites": {
                        "type": "integer",
                        "description": ("Controls the intensity of whites adjustment. Range: [-100, 100]: -100: Lowest whites; 0: Original whites; 100: Highest whites\n")
                    },  
                    "Blacks": {
                        "type": "integer",
                        "description": ("Controls the intensity of blacks adjustment. Range: [-100, 100]: -100: Lowest blacks; 0: Original blacks; 100: Highest blacks\n")
                    }, 
                    "Temp": {
                        "type": "integer",
                        "description": ("Controls the intensity of temperature adjustment. The temperature is defined in the range [2000K, 50000K].\n"
                                        "- 2000: Represents the lowest temperature (very warm, reddish/orange tones, similar to candlelight).\n"
                                        "- 5000: Represents neutral daylight (balanced white light, similar to midday sun).\n"
                                        "- 50000: Represents the highest temperature (very cool, bluish tones, similar to clear blue sky).\n")
                    },
                    "Tint": {
                        "type": "integer",
                        "description": ("Controls the intensity of tint adjustment. Range: [-100, 100]: -100: Lowest tint; 0: Original tint; 100: Highest tint\n")
                    },  
                    "Vibrance": {
                        "type": "integer",
                        "description": ("Controls the intensity of vibrance adjustment. Range: [-100, 100]: -100: Lowest vibrance; 0: Original vibrance; 100: Highest vibrance\n")
                    },  
                    "Saturation": {
                        "type": "integer",
                        "description": ("Controls the intensity of saturation adjustment. Range: [-100, 100]: -100: Lowest saturation; 0: Original saturation; 100: Highest saturation\n")
                    },
                    "Red": {
                        "type": "string",
                        "description": ("Controls the Hue, saturation, and brightness of the Red color. Given a list string, write the value you want to adjust directly in the string, for example `[0, 15, -20]`.\n")
                    },
                    "Orange": {
                        "type": "string",
                        "description": ("Controls the Hue, saturation, and brightness of the Orange color. Given a list string, write the value you want to adjust directly in the string, for example `[0, 15, -20]`.\n")
                    },
                    "Yellow": {
                        "type": "string",
                        "description": ("Controls the Hue, saturation, and brightness of the Yellow color. Given a list string, write the value you want to adjust directly in the string, for example `[0, 15, -20]`.\n")
                    },
                    "Green": {
                        "type": "string",
                        "description": ("Controls the Hue, saturation, and brightness of the Green color. Given a list string, write the value you want to adjust directly in the string, for example `[0, 15, -20]`.\n")
                    },
                    "Cyan": {
                        "type": "string",
                        "description": ("Controls the Hue, saturation, and brightness of the Cyan color. Given a list string, write the value you want to adjust directly in the string, for example `[0, 15, -20]`.\n")
                    },
                    "Blue": {
                        "type": "string",
                        "description": ("Controls the Hue, saturation, and brightness of the Blue color. Given a list string, write the value you want to adjust directly in the string, for example `[0, 15, -20]`.\n")
                    },
                    "Purple": {
                        "type": "string",
                        "description": ("Controls the Hue, saturation, and brightness of the Purple color. Given a list string, write the value you want to adjust directly in the string, for example `[0, 15, -20]`.\n")
                    },
                    "Magenta": {
                        "type": "string",
                        "description": ("Controls the Hue, saturation, and brightness of the Magenta color. Given a list string, write the value you want to adjust directly in the string, for example `[0, 15, -20]`.\n")
                    },
                    "reason": {
                        "type": "string",
                        "description": (
                            "Describe the main reasons for choosing this operation and this color_temperature_factor in no more than three sentences."
                        ),
                    },
                },
                "required": [
                    "Exposure",
                    "Contrast",
                    "Highlights",
                    "Shadows",
                    "Whites",
                    "Blacks",
                    "Temp",
                    "Tint",
                    "Vibrance",
                    "Saturation",
                    "Red",
                    "Orange",
                    "Yellow",
                    "Green",
                    "Cyan",
                    "Blue",
                    "Purple",
                    "Magenta",
                    "reason"
                ]
            }
        }
    ])
    def func_to_get_lightroom_adjustment(self, **kwargs):
        target_parameter = {
            "Exposure": kwargs["Exposure"],
            "Contrast": kwargs["Contrast"],
            "Highlights": kwargs["Highlights"],
            "Shadows": kwargs["Shadows"],
            "Whites": kwargs["Whites"],
            "Blacks": kwargs["Blacks"],
            "Temp": kwargs["Temp"],
            "Tint": kwargs["Tint"],
            "Vibrance": kwargs["Vibrance"],
            "Saturation": kwargs["Saturation"],
        }
        color_parameters = {
            "Red": safe_color_str_to_list(kwargs["Red"]),
            "Orange": safe_color_str_to_list(kwargs["Orange"]),
            "Yellow": safe_color_str_to_list(kwargs["Yellow"]),
            "Green": safe_color_str_to_list(kwargs["Green"]),
            "Cyan": safe_color_str_to_list(kwargs["Cyan"]),
            "Blue": safe_color_str_to_list(kwargs["Blue"]),
            "Purple": safe_color_str_to_list(kwargs["Purple"]),
            "Magenta": safe_color_str_to_list(kwargs["Magenta"]),
        }
        new_image_path = os.path.join(self.output_dir_path, f"{self.image_name}_{self.global_step+1}.jpg")
        new_histo_path = os.path.join(self.output_dir_path, f"{self.image_name}_{self.global_step+1}_histo.jpg")
        self.image_paths.append(new_image_path)
        self.histogram_paths.append(new_histo_path)
        self.current_status["current_image"] = new_image_path
        self.current_status["histogram_image"] = new_histo_path

        self.global_step += 1
        self.current_status["processing_image_step"] = self.global_step

        self.current_status["adjustment_status"] = target_parameter
        self.current_status["color_adjustment_status"] = color_parameters

        self.log_processing_step(f"Adjusting with {target_parameter}, {color_parameters}, reason: {kwargs['reason']}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting with {target_parameter}, {color_parameters}, reason: {kwargs['reason']}, generate image-{self.global_step}.")
        self.function_calls.append(["adjust_lightroom", target_parameter, color_parameters, kwargs['reason']])


        self._history_messages.append({"role": "assistant", "content": f"ADJUSTMENT: The retouching plan is: {target_parameter}, {color_parameters} and the reason is: {kwargs['reason']}"})
        self.user_messages.append({"role": "assistant", "content_type": "text", "content": f"{self.format_editing_params()}"})
        self.save_user_messages()
        self.user_messages.append({"role": "assistant", "content_type": "text", "content": f"{kwargs['reason']}"})
        self.save_user_messages()
        print(f"{'=' * 80}\n`func_to_get_lightroom_adjustment`, response: \n\n{target_parameter}")
        print(f"\n`func_to_get_lightroom_adjustment`, response: \n\n{color_parameters}")
        print(f"\n`func_to_get_lightroom_adjustment`, Reason: \n\n{kwargs['reason']}")

        set_slider_positions(target_parameter, self.config)
        set_color_slider_positions(color_parameters, self.config)
        get_GUI_preview_image(self.config, save_path=new_image_path)
        get_GUI_histo_image(self.config, save_path=new_histo_path)
        self.user_message_figure()

    @tool_doc([
        {
            "name": "satisfactory",
            "description": (
            "Confirm whether the current adjustment is satisfactory.\n"
            "If the current image is satisfactory and well expresses the artistic expectations in the historical record. Return True, and return the reasons for satisfaction and the interpretation of the final effect.\n"
            "If the current image is not satisfactory, return False, and describe in detail the reasons for dissatisfaction and the direction of improvement. Which parameters can no longer be adjusted, but which parameters need further adjustment.\n"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "is_satisfactory": {
                        "type": "boolean",
                        "description": """
                            Whether the current adjustment is satisfactory.
                        """
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation in no more than three sentences.
                        """,
                    },
                },
                "required": ["reason"]
            }
        }
    ])
    def satisfactory(self, is_satisfactory, reason):
        last_function_call = self.function_calls[-1]
        self.log_processing_step(f"The adjustment with parameter {self.current_status['adjustment_status']} is {'NOT' if not is_satisfactory else ''} satisfactory, reason: {reason}.")
        self.processing_log.append(f"The adjustment with parameter {self.current_status['adjustment_status']} is {'NOT' if not is_satisfactory else ''} satisfactory, reason: {reason}.")
        self.function_calls.append(["satisfactory", is_satisfactory, reason])
        self._history_messages.append({"role": "assistant", "content": f"ADJUSTMENT: The adjustment with parameter is{' NOT' if not is_satisfactory else ''} satisfactory, reason: {reason}."})
        self.user_messages.append({"role": "assistant", "content_type": "text", "content": f"The adjustment is{' NOT' if not is_satisfactory else ''} satisfactory. {reason}."})
        self.save_user_messages()
        print(self.processing_log[-1])

        self.set_satisfactory_status(is_satisfactory)

    @tool_doc([
        {
            "name": "func_return_responses",
            "description": """
                A function for GPT to structure and return its responses. Instead of providing responses in the content, 
                GPT should use this function to encapsulate all responses within the response parameter. This ensures a 
                consistent format for response handling and processing.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": """
                            The complete response content from GPT. This should contain all information, explanations, 
                            or answers that GPT wants to communicate. The content should be properly formatted with 
                            appropriate line breaks and spacing for readability. Markdown formatting is supported.
                        """
                    },
                },
                "required": ["response"]
            }
        }
    ])
    def func_to_return_responses(self, response):
        self._history_messages.append({"role": "assistant", "content": response})
        self.user_messages.append({"role": "assistant", "content_type": "text", "content": response})
        self.save_user_messages()
        print(f"{'=' * 80}\n`func_return_responses`, response: \n\n{response}")

    def log_processing_step(self, step_description):
        """
        Log a processing step to the log file.
        This method is useful for documenting the sequence of operations performed on the image.
        """
        with open(self.log_file_path, 'a') as log_file:
            log_file.write(step_description + "\n")

    def check_history_messages(self):
        """
        Print the history messages in a formatted manner.
        This method is useful for reviewing the sequence of operations performed on the image.
        """
        pretty_print_content(self._history_messages)

    @property
    def history_messages(self):
        """
        Customize the retrieval of history_messages, trimming content as needed.
        """
        if self.clip_history_messages:
            adjustment_list = []
            non_adjustment_list = []
            for item in self._history_messages:
                if item["content"].startswith("ADJUSTMENT"):
                    adjustment_list.append(item)
                else:
                    non_adjustment_list.append(item)
            return non_adjustment_list + adjustment_list[-3:] 
        return self._history_messages







