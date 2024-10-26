import os
import numpy as np
from PIL import Image, ImageEnhance
import skimage

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
        tool_docs = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'tool_doc'):
                tool_docs[attr_name] = attr.tool_doc
        return tool_docs

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
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this saturation_factor in no more than two sentences.
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
    # Change by Keda@2024/10
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
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this saturation_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["saturation_factor", "reason"]
            }
        },
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
                        "type": "int",
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
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this shadow_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["shadow_factor", "reason"]
            }
        },
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
                        "type": "int",
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
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this highlight_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["highlight_factor", "reason"]
            }
        },
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
                        "type": "int",
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
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this contrast_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["contrast_factor", "reason"]
            }
        },
        {
            "name": "adjust_brightness",
            "description": """
                Adjust the brightness of an input image by increasing or decreasing the overall light levels.

                Brightness adjustment is particularly useful for:
                
                - Correcting underexposed or overexposed images
                - Adding vibrancy to darker photos
                - Creating a soft or dramatic mood by altering brightness
                - Enhancing visibility of details in low-light images
                
                This adjustment modifies the brightness of all pixels in the image, with positive values increasing brightness and negative values reducing brightness.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "brightness_factor": {
                        "type": "int",
                        "description": """
                            Controls the intensity of brightness adjustment, similar to Lightroom's Brightness slider:
                            - -100: Minimum brightness (almost black)
                            - -50: Reduced brightness
                            - 0: Original brightness level
                            - 50: Increased brightness
                            - 100: Maximum brightness (brightest level)
                        """,
                    },
                    "reason": {
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this brightness_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["brightness_factor", "reason"]
            }
        },
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
                        "type": "int",
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
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this black_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["black_factor", "reason"]
            }
        },
        {
            "name": "adjust_gamma",
            "description": """
                Adjust the gamma of an input image, which modifies brightness and contrast in a non-linear way, enhancing midtones without overly affecting shadows or highlights.

                Gamma adjustment is particularly useful for:
                
                - Correcting images with improper exposure
                - Enhancing details in midtones
                - Brightening or darkening images for aesthetic effect
                - Compensating for display differences across devices
                
                This adjustment changes the gamma of all pixels, where values greater than 1 brighten the image and values less than 1 darken it.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "gamma_factor": {
                        "type": "float",
                        "description": """
                            Controls the intensity of gamma adjustment, similar to gamma sliders in photo editing software:
                            - < 1: Darkens the image
                            - 1: Original gamma level
                            - > 1: Brightens the image
                        """,
                    },
                    "reason": {
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this gamma_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["gamma_factor", "reason"]
            }
        },
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
                
                This adjustment modifies the brightest regions of the image, with positive values intensifying whites and negative values reducing their brightness.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "white_factor": {
                        "type": "float",
                        "description": """
                            Controls the intensity of white adjustment, similar to Lightroom's Whites slider:
                            - < 1: Reduces white intensity
                            - 1: Original white level
                            - > 1: Increases white intensity
                        """,
                    },
                    "reason": {
                        "type": "str",
                        "description": """
                            Describe the main reasons for choosing this operation and this white_factor in no more than two sentences.
                        """,
                    },
                },
                "required": ["white_factor", "reason"]
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

    def adjust_shadows(self, shadow_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_shadows_{shadow_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting shadows of {self.image_paths[-2]} with factor {shadow_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting shadows of image-{len(self.image_paths)-1} with factor {shadow_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_shadows", shadow_factor, reason])

        # Open an image file
        with Image.open(self.image_paths[-2]) as img:

            grayscale = img.convert("L")
            shadow_multiplier = 1 + (shadow_factor / 100.0)
            shadows = grayscale.point(lambda p: int(p * shadow_multiplier) if p <= 128 else p)
            img_shadowed = Image.merge("RGB", (shadows, shadows, shadows))
            img_adjusted = Image.blend(img, img_shadowed, 0.5)
            
            img_adjusted.save(self.image_paths[-1])
            print(self.processing_log[-1])
    
    def adjust_highlights(self, highlight_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_highlights_{highlight_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting highlights of {self.image_paths[-2]} with factor {highlight_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting highlights of image-{len(self.image_paths)-1} with factor {highlight_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_highlights", highlight_factor, reason])


        with Image.open(self.image_paths[-2]) as img:
            grayscale = img.convert("L")
            highlight_multiplier = 1 + (highlight_factor / 100.0)
            highlights = grayscale.point(lambda p: int(p * highlight_multiplier) if p > 128 else p)
            img_highlighted = Image.merge("RGB", (highlights, highlights, highlights))
            img_adjusted = Image.blend(img, img_highlighted, 0.5)
            
            img_adjusted.save(self.image_paths[-1])
            print(self.processing_log[-1])

    def adjust_contrast(self, contrast_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_contrast_{contrast_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting contrast of {self.image_paths[-2]} with factor {contrast_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting contrast of image-{len(self.image_paths)-1} with factor {contrast_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_contrast", contrast_factor, reason])

        with Image.open(self.image_paths[-2]) as img:
            # Map contrast_factor range to a multiplier effect
            contrast_multiplier = 1 + (contrast_factor / 100.0)
            
            # Enhance the image's contrast based on contrast_multiplier
            enhancer = ImageEnhance.Contrast(img)
            img_contrasted = enhancer.enhance(contrast_multiplier)
            
            # Save the adjusted image
            img_contrasted.save(self.image_paths[-1])
            print(self.processing_log[-1])
    
    def adjust_brightness(self, brightness_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_brightness_{brightness_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(f"Adjusting brightness of {self.image_paths[-2]} with factor {brightness_factor}, reason: {reason}, save to: {self.image_paths[-1]}")
        self.processing_log.append(f"Adjusting brightness of image-{len(self.image_paths)-1} with factor {brightness_factor}, generate image-{len(self.image_paths)}, reason: {reason}.")
        self.function_calls.append(["adjust_brightness", brightness_factor, reason])

        # Open an image file
        with Image.open(self.image_paths[-2]) as img:
            # Map brightness_factor range to a multiplier effect
            brightness_multiplier = 1 + (brightness_factor / 100.0)
            
            # Enhance the image's brightness based on brightness_multiplier
            enhancer = ImageEnhance.Brightness(img)
            img_brightened = enhancer.enhance(brightness_multiplier)
            
            # Save the adjusted image
            img_brightened.save(self.image_paths[-1])
            print(self.processing_log[-1])
            
    def adjust_blacks(self, black_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_blacks_{black_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(
            f"Adjusting blacks of {self.image_paths[-2]} with factor {black_factor}, reason: {reason}, save to: {self.image_paths[-1]}"
        )
        self.processing_log.append(
            f"Adjusting blacks of image-{len(self.image_paths)-1} with factor {black_factor}, generate image-{len(self.image_paths)}, reason: {reason}."
        )
        self.function_calls.append(["adjust_blacks", black_factor, reason])

        # Open the image and convert to grayscale to identify shadow areas
        with Image.open(self.image_paths[-2]) as img:
            img_gray = img.convert("L")
            img_gray_np = np.array(img_gray)

            # Calculate histogram and determine shadow threshold
            hist, _ = np.histogram(img_gray_np, bins=256, range=(0, 255))
            peak_intensity = np.argmax(hist[:128])  # Main peak in dark range
            shadow_threshold = int(peak_intensity * 0.5)  # Shadow threshold set to half the peak intensity

            # Convert the original image to a numpy array for adjustment
            img_array = np.array(img).astype(np.float32)

            # Apply black adjustment below the shadow threshold
            shadows = img_array < shadow_threshold
            black_multiplier = 1 + (black_factor / 100.0)
            img_array[shadows] *= black_multiplier
            img_array = np.clip(img_array, 0, 255)  # Clip values to [0, 255]

            # Convert adjusted array back to image format
            img_adjusted = Image.fromarray(img_array.astype(np.uint8))
            
            # Save the adjusted image
            img_adjusted.save(self.image_paths[-1])
            print(self.processing_log[-1])
            
    def adjust_gamma(self, gamma_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_gamma_{gamma_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(
            f"Adjusting gamma of {self.image_paths[-2]} with factor {gamma_factor}, reason: {reason}, save to: {self.image_paths[-1]}"
        )
        self.processing_log.append(
            f"Adjusting gamma of image-{len(self.image_paths)-1} with factor {gamma_factor}, generate image-{len(self.image_paths)}, reason: {reason}."
        )
        self.function_calls.append(["adjust_gamma", gamma_factor, reason])

        # Open and adjust the image's gamma
        with Image.open(self.image_paths[-2]) as img:
            # Convert the image to a numpy array and normalize to [0, 1]
            img_array = np.array(img).astype(np.float32) / 255.0
            
            # Apply gamma correction
            img_gamma_corrected = np.clip(np.power(img_array, gamma_factor), 0, 1)
            
            # Scale back to [0, 255] and convert to uint8
            img_gamma_corrected = (img_gamma_corrected * 255).astype(np.uint8)
            
            # Convert array back to image and save
            img_adjusted = Image.fromarray(img_gamma_corrected)
            img_adjusted.save(self.image_paths[-1])
            print(self.processing_log[-1])
            
    def adjust_whites(self, white_factor, reason):
        new_output_path = f"{len(self.image_paths)}_{self.image_name}_whites_{white_factor}.png"
        self.image_paths.append(os.path.join(self.output_dir_path, new_output_path))
        self.log_processing_step(
            f"Adjusting whites of {self.image_paths[-2]} with factor {white_factor}, reason: {reason}, save to: {self.image_paths[-1]}"
        )
        self.processing_log.append(
            f"Adjusting whites of image-{len(self.image_paths)-1} with factor {white_factor}, generate image-{len(self.image_paths)}, reason: {reason}."
        )
        self.function_calls.append(["adjust_whites", white_factor, reason])

        # Open the image and convert to grayscale to identify highlight areas
        with Image.open(self.image_paths[-2]) as img:
            img_gray = img.convert("L")
            img_gray_np = np.array(img_gray)

            # Calculate a dynamic white threshold based on the upper 5% intensity percentile
            white_threshold = np.percentile(img_gray_np, 95)
            print(f"Automatically calculated white threshold: {white_threshold}")

            # Convert original image to numpy array for white adjustment
            img_array = np.array(img).astype(np.float32)

            # Apply white adjustment above the white threshold
            mask = img_array > white_threshold
            img_array[mask] += (img_array[mask] - white_threshold) * (white_factor - 1)
            
            # Clip values to ensure they stay within [0, 255]
            img_array = np.clip(img_array, 0, 255).astype(np.uint8)
            
            # Convert adjusted array back to image format and save
            img_adjusted = Image.fromarray(img_array)
            img_adjusted.save(self.image_paths[-1])
            print(self.processing_log[-1])

    





