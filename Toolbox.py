import os

from PIL import Image, ImageEnhance


def tool_doc(description):
    def decorator(func):
        func.tool_doc = description
        return func
    return decorator


class ImageProcessingToolBoxes:

    def __init__(self, image_path, output_dir_path):
        self.output_dir_path = output_dir_path
        self.image_path = []
        self.output_path = []
        self.processing_log = []

        self.log_file_path = self.output_dir_path + "/processing_log.txt"
        self.image_path.append(image_path)

        self.image_name, _ = os.path.splitext(os.path.basename(image_path))
        
        def log_processing_step(step_description):
            with open(self.log_file_path, 'a') as log_file:
                log_file.write(step_description + "\n")
        
        self.log_processing_step = log_processing_step

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
                },
                "required": ["saturation_factor"]
            }
        }
    ])
    def adjust_saturation(self, saturation_factor):
        """
        Adjust the saturation of an input image using Pillow.
        
        Args:
            image_path (str): Path to the input image.
            saturation_factor (float): Factor to adjust saturation. 
                Values > 1 increase saturation, values < 1 decrease saturation.
            output_path (str): Path to save the adjusted image.
        """
        new_output_path = f"{len(self.output_path)}_{self.image_name}_saturation_{saturation_factor}.png"
        self.output_path.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting saturation of {self.image_path[-1]} to {saturation_factor}, save to {self.output_path[-1]}")

        # Open an image file
        with Image.open(self.image_path[-1]) as img:
            # Enhance the image's saturation
            enhancer = ImageEnhance.Color(img)
            img_enhanced = enhancer.enhance(saturation_factor)
            
            # Save the adjusted image
            img_enhanced.save(self.output_path[-1])
            print(f"The processed image has been saved as '{self.output_path[-1]}'")