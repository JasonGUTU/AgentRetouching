import os
from typing import List, Callable
import numpy as np
import cv2
from PIL import Image, ImageEnhance

def saturation(input_image_path: str, output_image_path: str, saturation_factor: float):
    """
    @2024/10/27
    Adjust the saturation of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- saturation_factor: float, the factor to adjust the saturation. [-100, 100]
    """
    ## !! Factor [0, 2] <- Lightroom  [-100, 100]
    saturation_factor = 0.01 * saturation_factor + 1
    with Image.open(input_image_path) as img:
        # Enhance the image's saturation
        enhancer = ImageEnhance.Color(img)
        img_enhanced = enhancer.enhance(saturation_factor)
        # Save the adjusted image
        img_enhanced.save(output_image_path)
        print(output_image_path)
        #print(f"The processed image has been saved as '{output_image_path}'")

def shadows(input_image_path: str, output_image_path: str, shadow_factor: float):
    """
    @2024/10/27
    Adjust the shadows of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- shadow_factor: float, the factor to adjust the shadows. [-100, 100]
    """
    ## !! Not need to be normalized. Factor == Lightroom  [-100, 100]
    img_raw = cv2.imread(input_image_path)
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    value = int(shadow_factor * 0.4)
    
    lim1 = 40
    lim2 = 120
    
    if value < 0:   
        v[v <= lim1] += abs(value)
        v[v <= lim2] -= abs(value)
        if abs(value) > lim1 // 2:
            v[v >= lim2] -= int(0.2 * abs(value))
            v[v <= int(0.2 * abs(value))] = int(0.2 * abs(value))
            v[v <= lim1] -= int(0.2 * abs(value))
        
    else:
        v[v <= lim2] += value
        v[v <= lim1] -= value 
        if value > lim1 // 2:
            v[v <= lim1] += int(0.2 * value)
            v[v >= lim2] += int(0.2 * value)


    final_hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    output_image = Image.fromarray(img)
    output_image.save(output_image_path)
    print(output_image_path)
    #print(f"The processed image has been saved as '{output_image_path}'")

def highlights(input_image_path: str, output_image_path: str, highlight_factor: float):
    """
    @2024/10/27
    Adjust the highlights of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- highlight_factor: float, the factor to adjust the highlights. [-100, 100]
    """
    ## !! Not need to be normalized. Factor == Lightroom  [-100, 100]
    img_raw = cv2.imread(input_image_path)
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    value = int(highlight_factor * 0.4)
    
    lim1 = 110
    lim2 = 205
    
    if value < 0:   
        v[v <= lim1] += abs(value)
        v[v <= lim2] -= abs(value)
        if abs(value) > (lim2 - lim1) // 8:
            v[v >= lim2] -= int(0.7 * abs(value))
            v[v <= int(0.7 * abs(value))] = int(0.5 * abs(value))
            v[v <= lim1] -= int(0.5 * abs(value))
        
    else:
        v[v <= lim2] += value
        v[v <= lim1] -= value 
        if value > (lim2 - lim1) // 8:
            v[v <= lim1] += int(0.5 * value)
            v[v >= 255 - int(0.5 * value)] = 255 - int(0.5 * value)
            v[v >= lim2] += int(0.5 * value)

    final_hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    output_image = Image.fromarray(img)
    output_image.save(output_image_path)
    print(output_image_path)

def contrast(input_image_path: str, output_image_path: str, contrast_factor: float):
    """
    @2024/10/27
    Adjust the contrast of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- contrast_factor: float, the factor to adjust the contrast. [-100, 100]
    """
    ## !! Factor [0, 2] <- Lightroom  [-100, 100]
    contrast_factor = 0.0036 * contrast_factor + 1.029
    with Image.open(input_image_path) as img:
        # Enhance the image's contrast
        enhancer = ImageEnhance.Contrast(img)
        img_contrasted = enhancer.enhance(contrast_factor)
        # Save the adjusted image
        img_contrasted.save(output_image_path)
        print(output_image_path)

def black(input_image_path: str, output_image_path: str, black_factor: float):
    """
    @2024/10/27
    Adjust the black of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- black_factor: float, the factor to adjust the black. [-100, 100]
    !! Best do not use [-100, -50] -> not working well.
    """
    ## !! Factor [0, 2] <- Lightroom  [-100, 100]
    black_factor = 0.01 * black_factor + 0.94
    with Image.open(input_image_path) as img:
        # Convert the image to grayscale for shadow analysis
        img_gray = img.convert("L")
        img_gray_np = np.array(img_gray)

        # Calculate histogram and automatically determine the shadow threshold
        hist, _ = np.histogram(img_gray_np, bins=256, range=(0, 255))
        peak_intensity = np.argmax(hist[:128])  # Find the main peak in the lower intensity range
        shadow_threshold = int(peak_intensity * 0.5)  # Set threshold as half the peak intensity
        img_array = np.array(img).astype(np.float32)

        # Apply black adjustment only to areas below the shadow threshold
        shadows = img_array < shadow_threshold
        img_array[shadows] *= black_factor
        img_array = np.clip(img_array, 0, 255)  # Ensure values stay within [0, 255]

        img_adjusted = Image.fromarray(img_array.astype(np.uint8))
        img_adjusted.save(output_image_path)
        print(output_image_path)

def white(input_image_path: str, output_image_path: str, white_factor: float):
    """
    @2024/10/27
    Adjust the white of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- black_factor: float, the factor to adjust the black. [-100, 100]
    """
    img_raw = cv2.imread(input_image_path)
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    value = int(white_factor * 0.4)
    
    lim1 = 110
    lim2 = 255
    
    if value < 0:   
        v[v >= lim1] -= abs(value)
        if abs(value) > int((lim2 - lim1) // 2):
            v[v < int(0.2 * abs(value))] = int(0.2 * abs(value))
            v[v <= lim1] -= int(0.2 * abs(value))
        
    else:
        v[v >= lim2 - value] = lim2 - value
        v[v >= lim1] += value 
        if value >= int((lim2 - lim1) // 2):
            v[v <= lim1] += int(0.2 * value)

    final_hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    output_image = Image.fromarray(img)
    output_image.save(output_image_path)
    print(output_image_path)


if __name__ == "__main__":
    saturation("berowra-landscape-photography.jpg", "cache/test/000.jpg", 100)
    shadows("berowra-landscape-photography.jpg", "cache/test/001.jpg", -100)
    highlights("berowra-landscape-photography.jpg", "cache/test/002.jpg", 100)
    contrast("berowra-landscape-photography.jpg", "cache/test/003.jpg", -100)
    black("berowra-landscape-photography.jpg", "cache/test/004.jpg", -40)
    white("berowra-landscape-photography.jpg", "cache/test/005.jpg", 100)