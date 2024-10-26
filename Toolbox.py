import os
from typing import List, Callable
from PIL import Image, ImageEnhance


def tool_doc(description):
    def decorator(func):
        func.tool_doc = description
        return func
    return decorator


class ImageProcessingToolBoxes:

    def __init__(self, image_path, output_dir_name):
        self.output_dir_path = output_dir_name
        if not os.path.exists(output_dir_name):
            os.makedirs(output_dir_name)
        else:
            raise FileExistsError(f"The directory '{output_dir_name}' already exists.")

        self.image_paths = []
        self.processing_log = []
        self.function_calls = []

        self.log_file_path = os.path.join(self.output_dir_path, "processing_log.txt")
        self.image_paths.append(image_path)

        self.image_name, _ = os.path.splitext(os.path.basename(image_path))
        
    def log_processing_step(self, step_description):
        with open(self.log_file_path, 'a') as log_file:
            log_file.write(step_description + "\n")
    
    def get_all_tool_docs(self):
        tool_docs = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'tool_doc'):
                tool_docs += attr.tool_doc
        return tool_docs
    
    def get_tool_docs(self, tools: List[Callable]):
        tool_docs = []
        for func in tools:
            if callable(func) and hasattr(func, 'tool_doc'):
                tool_docs += func.tool_doc
        return tool_docs
    
    def get_function_mapping(self):
        tool_docs = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'tool_doc'):
                tool_docs[attr.tool_doc[0]["name"]] = attr.__name__
        return tool_docs
    
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
                    }
                },
                "required": ["response"]
            }
        }
    ])
    def func_to_return_responses(self, response):
        

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
                        "type": "int",
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
        }
    ])
    def adjust_saturation(self, saturation_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_saturation_{saturation_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting saturation of {self.image_paths[-2]} to {saturation_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting saturation of image-{len(self.image_paths)-1} to {saturation_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_saturation", saturation_factor, reason])

        # Open an image file
        with Image.open(self.image_paths[-2]) as img:
            # Enhance the image's saturation
            enhancer = ImageEnhance.Color(img)
            img_enhanced = enhancer.enhance(saturation_factor)
            
            # Save the adjusted image
            img_enhanced.save(self.image_paths[-1])
            print(self.processing_log[-1])


