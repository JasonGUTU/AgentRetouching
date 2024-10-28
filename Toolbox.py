import os
from typing import List, Callable
import numpy as np
from Levenshtein import distance
from PIL import Image, ImageEnhance
from ImageProcessing import *

from Utils import pretty_print_content

def tool_doc(description):
    def decorator(func):
        func.tool_doc = description
        return func
    return decorator


class ImageProcessingToolBoxes:

    def __init__(self, image_path, output_dir_name, debug=False):  # TODO: 加 高分辨率图片
        self.output_dir_path = output_dir_name
        if not os.path.exists(output_dir_name):
            os.makedirs(output_dir_name)
        else:
            if debug:
                pass
            else:
                raise FileExistsError(f"The directory '{output_dir_name}' already exists.")

        self.image_paths = []
        self.processing_log = []
        self.function_calls = []
        self.history_messages = []

        self.processing_plan = []

        self.log_file_path = os.path.join(self.output_dir_path, "processing_log.txt")
        self.image_paths.append(image_path)

        self.image_name, _ = os.path.splitext(os.path.basename(image_path))

    def get_current_image_path(self):
        """Return the path of the most recently processed image
        This method is useful for retrieving the current state of the image after processing"""
        return self.image_paths[-1]
    
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
        function_names = [name for name in function_names if name not in ['func_to_return_responses', 'func_to_get_plan', 'undo_step']]
        return function_names.__str__()

    def finish_current_plan(self):
        """
        Finish the most first processing plan.
        This method is useful for finishing the most first processing plan.
        """
        if self.processing_plan:
            self.processing_plan = self.processing_plan[1:]

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

    @tool_doc([
        {
            "name": "undo_step",
            "description": """
                Undo the last image processing operation by reverting to the previous state in the image history stack.
                This function provides non-destructive editing capability by maintaining an image history stack.
                Each time an image processing operation is applied, the previous state is saved.
                
                Calling undo_step() will:

                - Revert the working image to the previous state
                - Return the previous image state for display/further processing
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation in no more than two sentences.
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
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_undo.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        last_function_call = self.function_calls[-1]
        self.log_processing_step(f"Undo adjusting of `{last_function_call[0]}` of {self.image_paths[-2]}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Undo the last operation `{last_function_call[0]}` with parameter `{last_function_call[1]}`, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["undo_step", reason])

        with Image.open(self.image_paths[-3]) as img:
            img.save(self.image_paths[-1])
            print(self.processing_log[-1])

    @tool_doc([
        {
            "name": "adjust_saturation",
            "description": """
                Adjust the saturation of an input image by modifying the intensity of the colors while preserving luminance.
    
                Saturation represents the intensity or purity of colors in an image. Increasing saturation makes colors more vivid 
                and intense, while decreasing it moves colors toward grayscale. This adjustment is particularly useful for:
    
                - Enhancing the vibrancy of sunrise/sunset photos
                - Making natural elements like foliage and flowers more striking
                - Adding punch to flat or hazy images
                - Creating artistic effects through dramatic color intensification
                - Toning down overly colorful scenes
                - Achieving a more muted, cinematic look
    
                The adjustment works by modifying color saturation in HSL (Hue, Saturation, Lightness) color space while 
                maintaining the original luminance values. This preserves the overall exposure and contrast of the image.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "saturation_factor": {
                        "type": "integer",
                        "description": """
                            Controls the intensity of the saturation adjustment, similar to Lightroom's Saturation slider:
                            - -100: Completely desaturated (grayscale)
                            - -50: Reduced saturation 
                            - 0: Original saturation 
                            - 50: Increased saturation 
                            - 100: Double saturation
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this saturation_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["saturation_factor", "reason"]
            }
        },
    ])
    def adjust_saturation(self, saturation_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_saturation_{saturation_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting saturation of {self.image_paths[-2]} to {saturation_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting saturation of image-{len(self.image_paths)-1} to {saturation_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_saturation", saturation_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting saturation of image-{len(self.image_paths)-1} to {saturation_factor}, reason: {reason}."})

        saturation(self.image_paths[-2], self.image_paths[-1], saturation_factor)

    @tool_doc([
        {
            "name": "adjust_shadows",
            "description": """
                Adjust the shadows of an input image by modifying the intensity of darker areas while preserving lighter tones.

                Shadow adjustment is particularly useful for:
                
                - Bringing out details in shadowed regions of photos
                - Enhancing contrast and depth in low-light images
                - Creating artistic effects by intensifying or softening shadows
                - Balancing exposure in high-contrast scenes
                
                This adjustment works by selectively modifying the darker pixels in the image, allowing fine-tuned control over shadow depth. 
                Positive values intensify shadows, while negative values reduce shadow depth.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "shadow_factor": {
                        "type": "integer",
                        "description": """
                            Controls the intensity of shadow adjustment, similar to Lightroom's Shadows slider:
                            - -100: Completely lightened shadows (maximum brightness)
                            - -50: Significantly reduced shadows
                            - 0: Original shadow level
                            - 50: Increased shadow depth
                            - 100: Maximum shadow depth (darker shadows)
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this shadow_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["shadow_factor", "reason"]
            }
        }
    ])
    def adjust_shadows(self, shadow_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_shadows_{shadow_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting shadows of {self.image_paths[-2]} with factor {shadow_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting shadows of image-{len(self.image_paths)-1} with factor {shadow_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_shadows", shadow_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting shadows of image-{len(self.image_paths)-1} with factor {shadow_factor}, reason: {reason}."})

        shadows(self.image_paths[-2], self.image_paths[-1], shadow_factor)
    
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
                            Describe the main reasons for choosing this operation and this highlight_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["highlight_factor", "reason"]
            }
        },
    ])
    def adjust_highlights(self, highlight_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_highlights_{highlight_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting highlights of {self.image_paths[-2]} with factor {highlight_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting highlights of image-{len(self.image_paths)-1} with factor {highlight_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_highlights", highlight_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting highlights of image-{len(self.image_paths)-1} with factor {highlight_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})

        highlights(self.image_paths[-2], self.image_paths[-1], highlight_factor)

    @tool_doc([
        {
            "name": "adjust_contrast",
            "description": """
                Adjust the contrast of an input image by enhancing or reducing the difference between light and dark areas.

                Contrast adjustment is particularly useful for:
                
                - Improving visibility in flat or low-contrast images
                - Adding depth to images for a more dynamic appearance
                - Reducing harsh contrasts for a softer look
                - Creating artistic effects through intense or subtle contrast
                
                This adjustment modifies contrast levels across the image, with positive values increasing contrast and negative values reducing contrast.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "contrast_factor": {
                        "type": "integer",
                        "description": """
                            Controls the intensity of contrast adjustment, similar to Lightroom's Contrast slider:
                            - -100: Minimum contrast (muted tones)
                            - -50: Reduced contrast
                            - 0: Original contrast level
                            - 50: Increased contrast
                            - 100: Maximum contrast (highest contrast)
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this contrast_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["contrast_factor", "reason"]
            }
        },
    ])
    def adjust_contrast(self, contrast_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_contrast_{contrast_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting contrast of {self.image_paths[-2]} with factor {contrast_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting contrast of image-{len(self.image_paths)-1} with factor {contrast_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_contrast", contrast_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting contrast of image-{len(self.image_paths)-1} with factor {contrast_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})

        contrast(self.image_paths[-2], self.image_paths[-1], contrast_factor)

    @tool_doc([
        {
            "name": "adjust_blacks",
            "description": """
                Adjust the black levels of an input image by intensifying or softening the darker regions, similar to Lightroom's black adjustment.

                Black level adjustment is particularly useful for:
                
                - Adding depth to shadowed areas
                - Increasing the sense of contrast by deepening blacks
                - Revealing hidden details in dark regions
                - Softening harsh black areas for a more muted look
                
                This adjustment modifies the darkest regions of the image, with positive values deepening the blacks and negative values softening them.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "black_factor": {
                        "type": "integer",
                        "description": """
                            Controls the intensity of black adjustment, similar to Lightroom's Blacks slider:
                            - -100: Minimum black level (lightened shadows)
                            - -50: Reduced black depth
                            - 0: Original black level
                            - 50: Increased black depth
                            - 100: Maximum black depth (deepest blacks)
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this black_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["black_factor", "reason"]
            }
        },
    ])
    def adjust_blacks(self, black_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_blacks_{black_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting blacks of {self.image_paths[-2]} with factor {black_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting blacks of image-{len(self.image_paths)-1} with factor {black_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_blacks", black_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting blacks of image-{len(self.image_paths)-1} with factor {black_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})

        black(self.image_paths[-2], self.image_paths[-1], black_factor)

    @tool_doc([
        {
            "name": "adjust_whites",
            "description": """
                Adjust the white levels of an input image by intensifying or softening the brighter regions, similar to Lightroom's white adjustment. 
                An automatic threshold detection is used to identify highlight areas based on image intensity percentiles.

                White level adjustment is particularly useful for:
                
                - Enhancing bright areas for added vibrancy
                - Controlling the brightness of highlighted areas
                - Softening intense whites for a balanced look
                - Bringing out subtle details in bright regions
                
                This adjustment modifies the brightest regions of the image, with positive values intensifying whites and negative values softening them.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "white_factor": {
                        "type": "int",
                        "description": """
                            Controls the intensity of white adjustment, similar to Lightroom's Whites slider:
                            - -100: Minimum white level (reduced highlights)
                            - -50: Moderately softened highlights
                            - 0: Original white level
                            - 50: Increased white intensity
                            - 100: Maximum white intensity (brightest highlights)
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this white_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["white_factor", "reason"]
            }
        } 
    ])
    def adjust_whites(self, white_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_whites_{white_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting whites of {self.image_paths[-2]} with factor {white_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting whites of image-{len(self.image_paths)-1} with factor {white_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_whites", white_factor, reason])
        self.history_messages.append({"role": "assistant", "content": f"Adjusting whites of image-{len(self.image_paths)-1} with factor {white_factor}, generate image-{len(self.image_paths)}, reason: {reason}."})

        white(self.image_paths[-2], self.image_paths[-1], white_factor)

    @tool_doc([
        {
            "name": "tone",
            "description": """
                Adjust the tone of an input image by modifying the green and red channel balance, shifting midtones towards either red or green.

                Tone adjustment is particularly useful for:
                
                - Adding subtle color shifts to enhance mood
                - Creating a cooler (green) or warmer (red) tone in midtones
                - Fine-tuning the overall visual feel of the image

                This adjustment modifies the green and red balance, where positive values increase red tones, creating a warmer look, and negative values increase green tones for a cooler look.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "tone_factor": {
                        "type": "float",
                        "description": """
                            Controls the intensity of tone adjustment, with positive values adding red tones and negative values adding green tones. Range: [-150, 150].
                            - -150: Maximum green tone (cooler midtones)
                            - 0: Original tone level
                            - 150: Maximum red tone (warmer midtones)
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this tone_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["tone_factor", "reason"]
            }
        }
    ])
    def adjust_tone(self, tone_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_tone_{tone_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(
            f"Adjusting tone of {self.image_paths[-2]} with factor {tone_factor}, reason: {reason}, save to: {self.image_paths[-1]}"
        )
        self.processing_log.append(
            f"Adjusting tone of image-{len(self.image_paths)-1} with factor {tone_factor}, generate image-{len(self.image_paths)}, reason: {reason}."
        )
        self.function_calls.append(["tone", tone_factor, reason])

        tone(self.image_paths[-2], self.image_paths[-1], tone_factor)

    @tool_doc([
        {
            "name": "color_temperature",
            "description": """
                Adjust the color temperature of an input image to make it appear warmer or cooler, similar to temperature adjustments in photo editing software. 
                The original image color temperature is assumed to be 6000K, and adjustments are applied accordingly.

                Color temperature adjustment is particularly useful for:
                
                - Correcting color balance in images shot under varying lighting conditions
                - Creating mood by warming or cooling the image
                - Enhancing colors in natural settings
                
                This adjustment modifies the blue and red color channels, where lower temperatures (<6000K) add warmth (yellow/orange tones), and higher temperatures (>6000K) add coolness (blue tones).
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "color_temperature_factor": {
                        "type": "float",
                        "description": """
                            Controls the intensity of color temperature adjustment in Kelvin. Range: [2000, 50000].
                            - 2000K: Maximum warmth (blue tones)
                            - 6000K: Original color temperature
                            - 50000K: Maximum coolness (yellow/orange tones)
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this color_temperature_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["color_temperature_factor", "reason"]
            }
        }
    ])
    def color_temperature(self, color_temperature_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_temperature_{color_temperature_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(
            f"Adjusting color temperature of {self.image_paths[-2]} with factor {color_temperature_factor}, reason: {reason}, save to: {self.image_paths[-1]}"
        )
        self.processing_log.append(
            f"Adjusting color temperature of image-{len(self.image_paths)-1} with factor {color_temperature_factor}, generate image-{len(self.image_paths)}, reason: {reason}."
        )
        self.function_calls.append(["color_temperature", color_temperature_factor, reason])

        color_temperature(self.image_paths[-2], self.image_paths[-1], color_temperature_factor)

    @tool_doc([
        {
            "name": "exposure",
            "description": """
                Adjust the exposure of an image, changing its overall brightness to achieve a balanced look.
                
                Exposure adjustment is particularly useful for:
                
                - Correcting underexposed or overexposed images
                - Enhancing details in very dark or very bright images
                - Creating artistic effects by brightening or darkening the image
                
                This adjustment modifies the exposure across all pixels, with positive values brightening the image and negative values darkening it.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "exposure_factor": {
                        "type": "float",
                        "description": """
                            Controls the intensity of exposure adjustment. Range: [-5, 5].
                            - -5: Maximum darkening (lowest exposure)
                            - 0: Original exposure
                            - 5: Maximum brightening (highest exposure)
                        """,
                    },
                    "reason": {
                        "type": "string",
                        "description": """
                            Describe the main reasons for choosing this operation and this exposure_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["exposure_factor", "reason"]
            }
        }
    ])
    def exposure(self, exposure_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_exposure_{exposure_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(
            f"Adjusting exposure of {self.image_paths[-2]} with factor {exposure_factor}, reason: {reason}, save to: {self.image_paths[-1]}"
        )
        self.processing_log.append(
            f"Adjusting exposure of image-{len(self.image_paths)-1} with factor {exposure_factor}, generate image-{len(self.image_paths)}, reason: {reason}."
        )
        self.function_calls.append(["exposure", exposure_factor, reason])

        exposure(self.image_paths[-2], self.image_paths[-1], exposure_factor)

