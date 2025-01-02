import os
from typing import List, Callable
import numpy as np
from Levenshtein import distance

import pyautogui

import cv2
import matplotlib.pyplot as plt
from io import BytesIO

from PIL import Image, ImageEnhance, ExifTags
from ImageProcessing import *

from Utils import pretty_print_content
from Toolbox import tool_doc
from GUIUtils import *


Toolbox_Config_Template = {
    "canva_topleft": (100, 100),
    "canva_bottomright": (100, 100),
    "pannel_topleft": (100, 100),
    "pannel_bottomright": (100, 100),
    "histogram_topleft": (100, 100),
    "histogram_bottomright": (100, 100),
    "controller_image_path": "",
    "adjustment_position": {
        "Exposure": [(100, 100), (100, 100), (100, 100)],
        "Contrast": [(100, 100), (100, 100), (100, 100)],
        "Highlights": [(100, 100), (100, 100), (100, 100)],
        "Shadows": [(100, 100), (100, 100), (100, 100)],
        "Whites": [(100, 100), (100, 100), (100, 100)],
        "Blacks": [(100, 100), (100, 100), (100, 100)],
        "Temp": [(100, 100), (100, 100), (100, 100)],
        "Tint": [(100, 100), (100, 100), (100, 100)],
        "Vibrance": [(100, 100), (100, 100), (100, 100)],
        "Saturation": [(100, 100), (100, 100), (100, 100)],
    },
    "HIDPI": 2,
    "background_color": [26, 26, 26]
}

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
    "histogram_image": "/path/to/histogram.png",
    "current_image": "/path/to/current.png",
    "processing_image_index": 0,
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
        self.history_messages = []  # Record of conversation history
        self.processing_plan = []
        self.plan_status = ""
        self.satisfactory_status = False
        self.log_file_path = os.path.join(self.output_dir_path, "processing_log.txt")

        self.get_current_GUI_status()
        
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
        self.current_status["processing_image_index"] = self.global_step
        self.current_status["adjustment_status"] = get_current_parameters(self.config)

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
            "description": """
                A function of GPT that generates and builds a specific plan for retouching based on the user's instructions and the analysis provided in the history information.
                GPT should carefully select and arrange the available image retouching adjustments. These adjustments are all adjustments in the Lightroom software.
                The available adjustments are: Exposure (-5.0, 5.0); Contrast (-100, 100); Highlights (-100, 100); Shadows (-100, 100); Whites (-100, 100); Blacks (-100, 100); Temp (-100, 100); Tint (-100, 100); Vibrance (-100, 100); Saturation (-100, 100). The initial value is 0.
                GPT records the parameters he wants to use by calling this function. For each adjustment, this function has a parameter position. Fill in the value directly in the parameter position. For Exposure, it is a floating point number. All others are integers.
            """,
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
                        "description": ("Controls the intensity of temperature adjustment. Range: [-100, 100]: -100: Lowest temperature; 0: Original temperature; 100: Highest temperature\n")
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
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this color_temperature_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["Exposure", "Contrast", "Highlights", "Shadows", "Whites", "Blacks", "Temp", "Tint", "Vibrance", "Saturation", "reason"]
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
        self.global_step += 1
        new_image_path = os.path.join(self.output_dir_path, f"{self.image_name}_{self.global_step}.jpg")
        new_histo_path = os.path.join(self.output_dir_path, f"{self.image_name}_{self.global_step}_histo.jpg")

        self.history_messages.append({"role": "assistant", "content": f"The retouching plan is: {target_parameter} and the reason is: {kwargs['reason']}"})
        print(f"{'=' * 80}\n`func_to_get_lightroom_adjustment`, response: \n\n{target_parameter} and the reason is: {kwargs['reason']}")

        self.image_paths.append(new_image_path)
        self.histogram_paths.append(new_histo_path)
        self.current_status["current_image"] = new_image_path
        self.current_status["histogram_image"] = new_histo_path
        self.current_status["processing_image_index"] = self.global_step
        self.current_status["adjustment_status"] = target_parameter

        self.log_processing_step(f"Adjusting with {target_parameter}, reason: {kwargs['reason']}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting with {target_parameter}, reason: {kwargs['reason']}, generate image-{self.global_step}.")
        self.function_calls.append(["adjust_lightroom", target_parameter, kwargs['reason']])

        set_slider_positions(target_parameter, self.config)
        get_GUI_preview_image(self.config, save_path=new_image_path)
        get_GUI_histo_image(self.config, save_path=new_histo_path)

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
        self.history_messages.append({"role": "assistant", "content": f"The adjustment with parameter {self.current_status['adjustment_status']} is {'NOT' if not is_satisfactory else ''} satisfactory, reason: {reason}."})
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
        self.history_messages.append({"role": "assistant", "content": response})
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
        pretty_print_content(self.history_messages)

    def __getattr__(self, name):
        if name == "history_messages" and self.clip_history_messages:
            # 在访问 my_list 时进行操作
            print("Dynamic operation on my_list...")
            return [x * 2 for x in self.__dict__["my_list"]]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")







