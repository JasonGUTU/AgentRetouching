import os
from typing import List, Callable
import numpy as np
from Levenshtein import distance

from PIL import Image, ImageEnhance, ExifTags
from ImageProcessing import *

from Utils import pretty_print_content


def tool_doc(description):
    def decorator(func):
        func.tool_doc = description
        return func
    return decorator


class ImageProcessingToolBoxes:

    def __init__(self, image_path, output_dir_name, debug=False, save_high_resolution=True, extension_name="png"):
        self.output_dir_path = output_dir_name
        self.extension_name = extension_name
        self.save_high_resolution = save_high_resolution
        if not os.path.exists(output_dir_name):
            os.makedirs(output_dir_name)
        else:
            if debug:
                pass
            else:
                raise FileExistsError(f"The directory '{output_dir_name}' already exists.")

        self.image_paths = []  # List of image paths for OpenAI to view
        self.hr_image_paths = []  # List of high-resolution image paths for OpenAI to view
        self.processing_log = []  # Log of processing steps
        self.function_calls = []  # Record of function calls
        self.history_messages = []  # Record of conversation history

        self.processing_plan = []

        self.log_file_path = os.path.join(self.output_dir_path, "processing_log.txt")
        self.image_name, _ = os.path.splitext(os.path.basename(image_path))

        self.plan_status = ""
        self.satisfactory_status = False

        # Load original image and downsample
        with Image.open(image_path) as img:
            width, height = img.size
            scale_factor = min(512/width, 512/height)
            new_width, new_height = int(width * scale_factor), int(height * scale_factor)
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 确保图片方向正确并保存
            if hasattr(img, '_getexif'): # 检查是否有EXIF数据
                try:
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation]=='Orientation':
                            break
                    exif=dict(img._getexif().items())

                    if orientation in exif:
                        if exif[orientation] == 3:
                            img_resized = img_resized.rotate(180, expand=True)
                            img = img.rotate(180, expand=True)
                        elif exif[orientation] == 6:
                            img_resized = img_resized.rotate(270, expand=True)
                            img = img.rotate(270, expand=True)
                        elif exif[orientation] == 8:
                            img_resized = img_resized.rotate(90, expand=True)
                            img = img.rotate(90, expand=True)
                except (AttributeError, KeyError, IndexError):
                    pass # 处理没有EXIF的情况

            resized_path = os.path.join(self.output_dir_path, f"0_{self.image_name}_resized.{self.extension_name}")
            img_resized.save(resized_path)
            self.image_paths.append(resized_path)

            hr_path = os.path.join(self.output_dir_path, f"0_{self.image_name}_hr.{self.extension_name}")
            self.hr_image_paths.append(hr_path)
            if self.save_high_resolution:
                img.save(hr_path)

    def set_plan_status(self, status):
        self.plan_status = status

    def set_satisfactory_status(self, status):
        self.satisfactory_status = status

    def get_current_image_path(self, image_number=1):
        """Return the path of the most recently processed image
        This method is useful for retrieving the current state of the image after processing"""
        if image_number == 1:
            return self.image_paths[-1]
        else:
            return self.image_paths[-image_number:]
    
    def check_history_messages(self):
        """
        Print the history messages in a formatted manner.
        This method is useful for reviewing the sequence of operations performed on the image.
        """
        pretty_print_content(self.history_messages)
        
    def log_processing_step(self, step_description):
        """
        Log a processing step to the log file.
        This method is useful for documenting the sequence of operations performed on the image.
        """
        with open(self.log_file_path, 'a') as log_file:
            log_file.write(step_description + "\n")
    
    def get_all_tool_docs(self):
        """
        Get all tool documentation.
        This method is useful for retrieving the documentation of all available tools.
        """
        tool_docs = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'tool_doc'):
                tool_docs += attr.tool_doc
        return tool_docs
    
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
    
    def get_function_names(self):
        """
        Get a list of function names excluding the special functions.
        This method is useful for retrieving the list of function names excluding the special functions.
        """
        function_names = list(self.get_function_mapping().keys())
        function_names = [name for name in function_names if name not in ['func_to_return_responses', 'func_to_get_plan', 'undo_step', 'satisfactory']]
        return function_names.__str__()

    def get_function_short_description(self):
        function_names = list(self.get_function_mapping().keys())
        function_names = [name for name in function_names if name not in ['func_to_return_responses', 'func_to_get_plan', 'undo_step']]

        function_short_descriptions = []

        for name in function_names:
            attr = getattr(self, name)
            if callable(attr) and attr.__doc__:
                doc = attr.__doc__
                function_short_descriptions.append(f"{doc}")
        
        return "\n".join(function_short_descriptions)

    @tool_doc([
        {
            "name": "func_to_return_responses",
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
        print(f"\n\n`func_to_return_responses`, response: \n\n{response}")

    @tool_doc([
        {
            "name": "func_to_get_plan",
            "description": """
                A function for GPT to generate and structure a retouching plan based on the user's instructions and the analysis provided in the historical information. 
                GPT should carefully select and arrange the available image retouching functions, considering the sequence in which they are applied, as the order is crucial for the overall outcome. 
                The response should be a Python-readable list of function names in string format, maintaining the exact order chosen for the retouching plan. 
                The available functions are provided in the user's instruction. Example response format: "['adjust_blacks', 'adjust_brightness', 'adjust_contrast', 'adjust_gamma', 'adjust_highlights', 'adjust_saturation', 'adjust_shadows', 'adjust_whites']".
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": """
                            The full retouching plan, represented as a Python-readable list of function names in string format. The order of the functions is crucial, and each function should be listed 
                            in the sequence chosen by GPT based on the analysis and the user's instructions.
                        """
                    }
                },
                "required": ["response"]
            }
        }
    ])
    def func_to_get_plan(self, response):
        self.history_messages.append({"role": "assistant", "content": f"The retouching plan is: {response}"})
        print(f"\n\n`func_to_get_plan`, response: \n\n{response}")

        # Try to parse the response as a list
        try:
            plan_list = eval(response)
        except:
            # If parsing fails, try using string processing method
            plan_list = response.strip("[]").replace("'", "").replace('"', "").split(",")
            plan_list = [item.strip() for item in plan_list]

        # Get all possible function names
        valid_functions = set(self.get_function_mapping().keys())

        # Filter and replace invalid function names
        filtered_plan = []
        for func in plan_list:
            if func in valid_functions:
                filtered_plan.append(func)
            else:
                # Find the most similar valid function name
                most_similar = max(valid_functions, key=lambda x: self.similarity(func, x))
                filtered_plan.append(most_similar)

        print(f"Plan after parsing: {filtered_plan}")
        self.processing_plan = filtered_plan

    def similarity(self, a, b):
        max_len = max(len(a), len(b))
        return 1 - distance(a, b) / max_len

    def parse_lr_path_to_hr_path(self, lr_path):
        """ Convert low resolution path to high resolution path """
        base_name = os.path.splitext(os.path.basename(lr_path))[0]
        hr_name = base_name + "_hr" + os.path.splitext(lr_path)[1]
        hr_path = os.path.join(os.path.dirname(lr_path), hr_name)
        return hr_path

    def finish_current_plan(self):
        """
        Finish the most first processing plan.
        This method is useful for finishing the most first processing plan.
        """
        self.plan_status = "finished"
        if self.processing_plan:
            self.processing_plan = self.processing_plan[1:]

    @tool_doc([
        {
            "name": "satisfactory",
            "description": (
                "Confirm the current adjustment is satisfactory.\n"
                "Proceed to the next image processing operation after confirming the current adjustment is satisfactory.\n"
                "This function maintains the workflow progression while preserving the successful adjustment in the image history.\n"
                "The current state becomes a confirmed checkpoint in the editing process.\n"
            ),
            "parameters": {
                "type": "object",
                "properties": {
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
    def satisfactory(self, reason):
        last_function_call = self.function_calls[-1]
        self.log_processing_step(f"Confirm the adjustment `{last_function_call[0]}` with parameter `{last_function_call[1]}` is satisfactory, reason: {reason}.")
        self.processing_log.append(f"Confirm the adjustment `{last_function_call[0]}` with parameter `{last_function_call[1]}` is satisfactory, reason: {reason}.")
        self.function_calls.append(["satisfactory", reason])
        self.history_messages.append({"role": "assistant", "content": f"Confirm the adjustment `{last_function_call[0]}` with parameter `{last_function_call[1]}` is satisfactory, reason: {reason}."})
        print(self.processing_log[-1])

        self.set_satisfactory_status(True)

    @tool_doc([
        {
            "name": "undo_step",
            "description": (
                "Undo the last image processing operation by reverting to the previous state in the image history stack.\n"
                "This function provides non-destructive editing capability by maintaining an image history stack.\n"
                "Each time an image processing operation is applied, the previous state is saved.\n"
                
                "Calling undo_step() will:\n"

                "- Revert the working image to the previous state\n"
                "- Return the previous image state for display/further processing\n"
            ),
            "parameters": {
                "type": "object",
                "properties": {
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
    def undo_step(self, reason):
        if len(self.image_paths) < 2:
            raise ValueError("Cannot undo operation because there are not enough image paths.")
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_undo.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        last_function_call = self.function_calls[-1]
        self.log_processing_step(f"Undo adjusting of `{last_function_call[0]}` of {self.image_paths[-2]}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Undo the last operation `{last_function_call[0]}` with parameter `{last_function_call[1]}`, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["undo_step", reason])
        self.history_messages.append({"role": "assistant", "content": f"Undo the last operation `{last_function_call[0]}` with parameter `{last_function_call[1]}`, reason: {reason}."})
        print(self.processing_log[-1])

        with Image.open(self.image_paths[-3]) as img:
            img.save(self.image_paths[-1])
        
        if self.save_high_resolution:
            with Image.open(self.hr_image_paths[-3]) as img:
                img.save(self.hr_image_paths[-1])   

    @tool_doc([
        {
            "name": "adjust_saturation",
            "description": (
                "Adjust the saturation of an input image by modifying the intensity of the colors while preserving luminance.\n"
                "Saturation represents the intensity or purity of colors in an image. Increasing saturation makes colors more vivid "
                "and intense, while decreasing it moves colors toward grayscale. This adjustment is particularly useful for:\n"
    
                "- Enhancing the vibrancy of sunrise/sunset photos\n"
                "- Making natural elements like foliage and flowers more striking\n"
                "- Adding punch to flat or hazy images\n"
                "- Creating artistic effects through dramatic color intensification\n"
                "- Toning down overly colorful scenes\n"
                "- Achieving a more muted, cinematic look\n"
    
                "The adjustment works by modifying color saturation in HSL (Hue, Saturation, Lightness) color space while "
                "maintaining the original luminance values. This preserves the overall exposure and contrast of the image."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "saturation_factor": {
                        "type": "integer",
                        "description": (
                            "Controls the intensity of the saturation adjustment, similar to Lightroom's Saturation slider:\n"
                            "- -100: Completely desaturated (grayscale)\n"
                            "- -50: Reduced saturation \n"
                            "- 0: Original saturation \n"
                            "- 50: Increased saturation \n"
                            "- 100: Double saturation\n"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this saturation_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["saturation_factor", "reason"]
            }
        },
    ])
    def adjust_saturation(self, saturation_factor, reason):
        (
            "- Adjust Saturation: Which parts of the image benefit from changes in saturation? Increasing saturation can make colors more vivid and bold, enhancing emotional impact, while desaturating can give a more muted, artistic feel, focusing attention on texture and composition rather than color.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_saturation_{saturation_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting saturation of {self.image_paths[-2]} to {saturation_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting saturation of image-{len(self.image_paths)-1} to {saturation_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_saturation", saturation_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting saturation of image-{len(self.image_paths)-1} to {saturation_factor}, reason: {reason}."})
        print(self.processing_log[-1])

        saturation(self.image_paths[-2], self.image_paths[-1], saturation_factor)

        if self.save_high_resolution:
            saturation(self.hr_image_paths[-2], self.hr_image_paths[-1], saturation_factor)

    @tool_doc([
        {
            "name": "adjust_shadows",
            "description": (
                "Adjust the shadows of an input image by modifying the intensity of darker areas while preserving lighter tones.\n"
                "Shadow adjustment is particularly useful for:\n"
                
                "- Bringing out details in shadowed regions of photos\n"
                "- Enhancing contrast and depth in low-light images\n"
                "- Creating artistic effects by intensifying or softening shadows\n"
                "- Balancing exposure in high-contrast scenes\n"
                
                "This adjustment works by selectively modifying the darker pixels in the image, allowing fine-tuned control over shadow depth. \n"
                "Positive values intensify shadows, while negative values reduce shadow depth."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "shadow_factor": {
                        "type": "integer",
                        "description": (
                            "Controls the intensity of shadow adjustment, similar to Lightroom's Shadows slider:\n"
                            "- -100: Completely lightened shadows (maximum brightness)\n"
                            "- -50: Significantly reduced shadows\n"
                            "- 0: Original shadow level\n"
                            "- 50: Increased shadow depth\n"
                            "- 100: Maximum shadow depth (darker shadows)\n"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this shadow_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["shadow_factor", "reason"]
            }
        }
    ])
    def adjust_shadows(self, shadow_factor, reason):
        (
            "- Adjust Shadows: How should the shadows be handled to influence the image's mood? Deepening shadows might add mystery or drama, while lifting shadows can soften the contrast and reveal more detail in darker areas, creating a gentler and more open feeling.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_shadows_{shadow_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting shadows of {self.image_paths[-2]} with factor {shadow_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting shadows of image-{len(self.image_paths)-1} with factor {shadow_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_shadows", shadow_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting shadows of image-{len(self.image_paths)-1} with factor {shadow_factor}, reason: {reason}."})
        print(self.processing_log[-1])

        shadows(self.image_paths[-2], self.image_paths[-1], shadow_factor)

        if self.save_high_resolution:
            shadows(self.hr_image_paths[-2], self.hr_image_paths[-1], shadow_factor)

    @tool_doc([
        {
            "name": "adjust_highlights",
            "description": """
                Adjust the highlights of an input image by modifying the intensity of lighter areas while preserving darker tones.
                Highlight adjustment is particularly useful for:
                
                - Reducing overexposed regions in bright scenes
                - Enhancing contrast by softening or intensifying highlights
                - Adding detail to high-contrast areas
                - Creating artistic effects through selective highlight manipulation
                
                This adjustment works by selectively modifying the brighter pixels in the image, allowing fine-tuned control over highlight 
                intensity. Positive values intensify highlights, while negative values reduce highlight brightness.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "highlight_factor": {
                        "type": "integer",
                        "description": """
                            Controls the intensity of highlight adjustment, similar to Lightroom's Highlights slider:
                            - -100: Completely reduced highlights (muted highlights)
                            - -50: Significantly reduced highlights
                            - 0: Original highlight level
                            - 50: Increased highlight intensity
                            - 100: Maximum highlight intensity (brightest highlights)
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this highlight_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["highlight_factor", "reason"]
            }
        },
    ])
    def adjust_highlights(self, highlight_factor, reason):
        (
            "- Adjust Highlights: How will adjusting the highlights affect the brightest areas of the image? Increasing highlights can make these areas pop and appear more vibrant, while reducing highlights may prevent overexposure and recover lost details in bright areas, giving the image a more balanced look.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_highlights_{highlight_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting highlights of {self.image_paths[-2]} with factor {highlight_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting highlights of image-{len(self.image_paths)-1} with factor {highlight_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_highlights", highlight_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting highlights of image-{len(self.image_paths)-1} with factor {highlight_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})
        print(self.processing_log[-1])

        highlights(self.image_paths[-2], self.image_paths[-1], highlight_factor)

        if self.save_high_resolution:
            highlights(self.hr_image_paths[-2], self.hr_image_paths[-1], highlight_factor)

    @tool_doc([
        {
            "name": "adjust_contrast",
            "description": (
                "Adjust the contrast of an input image by enhancing or reducing the difference between light and dark areas.\n"

                "Contrast adjustment is particularly useful for:\n"
                
                "- Improving visibility in flat or low-contrast images\n"
                "- Adding depth to images for a more dynamic appearance\n"
                "- Reducing harsh contrasts for a softer look\n"
                "- Creating artistic effects through intense or subtle contrast\n"
                
                "This adjustment modifies contrast levels across the image, with positive values increasing contrast and negative values reducing contrast."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contrast_factor": {
                        "type": "integer",
                        "description": (
                            "Controls the intensity of contrast adjustment, similar to Lightroom's Contrast slider:\n"
                            "- -100: Minimum contrast (muted tones)\n"
                            "- -50: Reduced contrast\n"
                            "- 0: Original contrast level\n"
                            "- 50: Increased contrast\n"
                            "- 100: Maximum contrast (highest contrast)\n"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this contrast_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["contrast_factor", "reason"]
            }
        },
    ])
    def adjust_contrast(self, contrast_factor, reason):
        (
            "- Adjust Contrast: Should the contrast be modified to emphasize the difference between light and dark areas? For instance, increasing contrast can make the subject more striking and the details more pronounced, while lowering contrast may create a softer, more ethereal feel.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_contrast_{contrast_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting contrast of {self.image_paths[-2]} with factor {contrast_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting contrast of image-{len(self.image_paths)-1} with factor {contrast_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_contrast", contrast_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting contrast of image-{len(self.image_paths)-1} with factor {contrast_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})
        print(self.processing_log[-1])

        contrast(self.image_paths[-2], self.image_paths[-1], contrast_factor)

        if self.save_high_resolution:
            contrast(self.hr_image_paths[-2], self.hr_image_paths[-1], contrast_factor)

    @tool_doc([
        {
            "name": "adjust_blacks",
            "description": (
                "Adjust the black levels of an input image by intensifying or softening the darker regions, similar to Lightroom's black adjustment.\n"

                "Black level adjustment is particularly useful for:\n"
                
                "- Adding depth to shadowed areas\n"
                "- Increasing the sense of contrast by deepening blacks\n"
                "- Revealing hidden details in dark regions\n"
                "- Softening harsh black areas for a more muted look\n"
                
                "This adjustment modifies the darkest regions of the image, with positive values deepening the blacks and negative values softening them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "black_factor": {
                        "type": "integer",
                        "description": (
                            "Controls the intensity of black adjustment, similar to Lightroom's Blacks slider:\n"
                            "- -100: Minimum black level (lightened shadows)\n"
                            "- -50: Reduced black depth\n"
                            "- 0: Original black level\n"
                            "- 50: Increased black depth\n"
                            "- 100: Maximum black depth (deepest blacks)\n"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this black_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["black_factor", "reason"]
            }
        },
    ])
    def adjust_blacks(self, black_factor, reason):
        (
            "- Adjust Blacks: Should the black levels be deepened to add intensity to the image? For example, darkening the blacks can increase contrast and make the image more dramatic, while raising the black levels could reveal more detail in the shadowed areas, softening the overall mood.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_blacks_{black_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting blacks of {self.image_paths[-2]} with factor {black_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting blacks of image-{len(self.image_paths)-1} with factor {black_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_blacks", black_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting blacks of image-{len(self.image_paths)-1} with factor {black_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})
        print(self.processing_log[-1])

        black(self.image_paths[-2], self.image_paths[-1], black_factor)

        if self.save_high_resolution:
            black(self.hr_image_paths[-2], self.hr_image_paths[-1], black_factor)

    @tool_doc([
        {
            "name": "adjust_whites",
            "description": (
                "Adjust the white levels of an input image by intensifying or softening the brighter regions, similar to Lightroom's white adjustment. \n"
                "An automatic threshold detection is used to identify highlight areas based on image intensity percentiles.\n"

                "White level adjustment is particularly useful for:\n"
                
                "- Enhancing bright areas for added vibrancy\n"
                "- Controlling the brightness of highlighted areas\n"
                "- Softening intense whites for a balanced look\n"
                "- Bringing out subtle details in bright regions\n"
                
                "This adjustment modifies the brightest regions of the image, with positive values intensifying whites and negative values softening them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "white_factor": {
                        "type": "integer",
                        "description": (
                            "Controls the intensity of white adjustment, similar to Lightroom's Whites slider:\n"
                            "- -100: Minimum white level (reduced highlights)\n"
                            "- -50: Moderately softened highlights\n"
                            "- 0: Original white level\n"
                            "- 50: Increased white intensity\n"
                            "- 100: Maximum white intensity (brightest highlights)\n"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this white_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["white_factor", "reason"]
            }
        } 
    ])
    def adjust_whites(self, white_factor, reason):
        (
            "- Adjust Whites: Will adjusting the white levels change the clarity of the brightest spots in the image? Increasing the whites can make the light areas more dazzling and eye-catching, while reducing the whites might tone down the overall brightness and create a more cohesive, understated look.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_whites_{white_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting whites of {self.image_paths[-2]} with factor {white_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting whites of image-{len(self.image_paths)-1} with factor {white_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_whites", white_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting whites of image-{len(self.image_paths)-1} with factor {white_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})
        print(self.processing_log[-1])

        white(self.image_paths[-2], self.image_paths[-1], white_factor)

        if self.save_high_resolution:
            white(self.hr_image_paths[-2], self.hr_image_paths[-1], white_factor)

    @tool_doc([
        {
            "name": "adjust_tone",
            "description": (
                "Adjust the tone of an input image by modifying the green and red channel balance, shifting midtones towards either red or green.\n"

                "Tone adjustment is particularly useful for:\n"
                
                "- Adding subtle color shifts to enhance mood\n"
                "- Creating a cooler (green) or warmer (red) tone in midtones\n"
                "- Fine-tuning the overall visual feel of the image\n"

                "This adjustment modifies the green and red balance, where positive values increase red tones, creating a warmer look, and negative values increase green tones for a cooler look."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tone_factor": {
                        "type": "integer",
                        "description": (
                            "Controls the intensity of tone adjustment, with positive values adding red tones and negative values adding green tones. Range: [-150, 150].\n"
                            "- -150: Maximum green tone (cooler midtones)\n"
                            "- 0: Original tone level\n"
                            "- 150: Maximum red tone (warmer midtones)\n"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this tone_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["tone_factor", "reason"]
            }
        }
    ])
    def adjust_tone(self, tone_factor, reason):
        (
            "- Adjust Tone: How will tone adjustments affect the overall mood of the image? Increasing the tone towards red can make the image feel warmer and more vibrant, while shifting the tone towards green can create a cooler, more serene feel.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_tone_{tone_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting tone of {self.image_paths[-2]} with factor {tone_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting tone of image-{len(self.image_paths)-1} with factor {tone_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["tone", tone_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting tone of image-{len(self.image_paths)-1} with factor {tone_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})
        print(self.processing_log[-1])

        tone(self.image_paths[-2], self.image_paths[-1], tone_factor)

        if self.save_high_resolution:
            tone(self.hr_image_paths[-2], self.hr_image_paths[-1], tone_factor)

    @tool_doc([
        {
            "name": "adjust_color_temperature",
            "description": (
                "Adjust the color temperature of an input image to make it appear warmer or cooler, similar to temperature adjustments in photo editing software. \n"
                "The original image color temperature is assumed to be 6000K, and adjustments are applied accordingly.\n"

                "Color temperature adjustment is particularly useful for:\n"
                
                "- Correcting color balance in images shot under varying lighting conditions\n"
                "- Creating mood by warming or cooling the image\n"
                "- Enhancing colors in natural settings\n"
                
                "This adjustment modifies the blue and red color channels, where lower temperatures (<6000K) add warmth (yellow/orange tones), and higher temperatures (>6000K) add coolness (blue tones)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "color_temperature_factor": {
                        "type": "integer",
                        "description": (
                            "Controls the intensity of color temperature adjustment in Kelvin. Range: [2000, 50000].\n"
                            "- 2000: 2000K Maximum warmth (blue tones)\n"
                            "- 6000: 6000K Original color temperature\n"
                            "- 50000: 50000K Maximum coolness (yellow/orange tones)\n"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this color_temperature_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["color_temperature_factor", "reason"]
            }
        }
    ])
    def adjust_color_temperature(self, color_temperature_factor, reason):
        (
            "- Adjust Color Temperature: How will color temperature adjustments affect the overall mood of the image? Lowering the temperature can make the image feel cooler and more serene, while raising the temperature can make the image feel warmer and more vibrant.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_temperature_{color_temperature_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting color temperature of {self.image_paths[-2]} with factor {color_temperature_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting color temperature of image-{len(self.image_paths)-1} with factor {color_temperature_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["color_temperature", color_temperature_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting color temperature of image-{len(self.image_paths)-1} with factor {color_temperature_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})
        print(self.processing_log[-1])

        color_temperature(self.image_paths[-2], self.image_paths[-1], color_temperature_factor)

        if self.save_high_resolution:
            color_temperature(self.hr_image_paths[-2], self.hr_image_paths[-1], color_temperature_factor)

    @tool_doc([
        {
            "name": "adjust_exposure",
            "description": (
                "Adjust the exposure of an image, changing its overall brightness to achieve a balanced look.\n"
                
                "Exposure adjustment is particularly useful for:\n"
                
                "- Correcting underexposed or overexposed images\n"
                "- Enhancing details in very dark or very bright images\n"
                "- Creating artistic effects by brightening or darkening the image\n"
                
                "This adjustment modifies the exposure across all pixels, with positive values brightening the image and negative values darkening it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "exposure_factor": {
                        "type": "number",
                        "description": (
                            "Controls the intensity of exposure adjustment. Range: [-5, 5].\n"
                            "- -5: Maximum darkening (lowest exposure)\n"
                            "- 0: Original exposure\n"
                            "- 5: Maximum brightening (highest exposure)\n"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this exposure_factor in no more than three sentences.
                        """,
                    },
                },
                "required": ["exposure_factor", "reason"]
            }
        }
    ])
    def adjust_exposure(self, exposure_factor, reason):
        (
            "- Adjust Exposure: How will exposure adjustments affect the overall mood of the image? Increasing exposure might make the image feel more vibrant and energetic, while reducing exposure can add a sense of subtlety or calmness, enhancing any moody or low-light elements.\n"
        )
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_exposure_{exposure_factor}.{self.extension_name}"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.hr_image_paths.append(os.path.join(self.output_dir_path, self.parse_lr_path_to_hr_path(new_output_path)))

        self.log_processing_step(f"Adjusting exposure of {self.image_paths[-2]} with factor {exposure_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting exposure of image-{len(self.image_paths)-1} with factor {exposure_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["exposure", exposure_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting exposure of image-{len(self.image_paths)-1} with factor {exposure_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})
        print(self.processing_log[-1])

        exposure(self.image_paths[-2], self.image_paths[-1], exposure_factor)

        if self.save_high_resolution:
            exposure(self.hr_image_paths[-2], self.hr_image_paths[-1], exposure_factor)

