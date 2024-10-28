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

def tone(input_image_path: str, output_image_path: str, tone_factor: float):
    """
    @2024/10/27
    Adjust the tone of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- tone_factor: float, the factor to adjust the tone. [-150, 150]
    """
    img_raw = cv2.imread(input_image_path)
    value = -1 * tone_factor
    b, g, r = cv2.split(img_raw)
    
    if value >= 0:
        lim = 255 - value
        g[g > lim] = 255
        g[g <= lim] += value
      
    else:
        lim = 0 - value
        g[g < lim] = 0
        g[g >= lim] -= abs(value)

    
    image = cv2.merge((b, g, r))
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    output_image = Image.fromarray(img)
    output_image.save(output_image_path)
    print(output_image_path)

def color_temperature(input_image_path: str, output_image_path: str, color_temperature_factor: float):
    """
    @2024/10/27
    Adjust the color temperature of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- color_temperature_factor: float, the factor to adjust the color temperature. [2000, 50000]
    !! We set the original color temperature to 6000K.
    """
    img_raw = cv2.imread(input_image_path)
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)
    original_temp = 6000
    value = np.clip(color_temperature_factor, 2000, 50000)  # Ensure value is within the specified range
    if value > original_temp:
        value = ((value - original_temp) / (50000 - original_temp)) * 100  # Map to 0-100
    else:
        value = ((value - original_temp) / (original_temp - 2000)) * 100  # Map to -100-0
    print(value)
    value = np.round(value)  # Convert to uint8 to avoid casting issues
    b, g, r = cv2.split(img)
    value = int(-1 * value)
    print(value)
    if value >= 0:
        lim = 255 - value
        r[r > lim] = 255
        r[r <= lim] += value
        
        lim1 = 0 + value
        b[b < lim1] = 0
        b[b >= lim1] -= value
        
    else:
        lim = 0 - value
        r[r < lim] = 0
        r[r >= lim] -= abs(value)
        
        lim = 255 - abs(value)
        b[b > lim] = 255
        b[b <= lim] += abs(value)

    image = cv2.merge((b, g, r))
    #image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert to RGB before saving
    output_image = Image.fromarray(image)
    output_image.save(output_image_path)
    print(output_image_path)

def exposure(input_image_path: str, output_image_path: str, exposure_factor: float):
    """
    @2024/10/27
    Adjust the exposure of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- exposure_factor: float, the factor to adjust the exposure. [-5, 5]
    """
    with Image.open(input_image_path) as img:
        # Convert to NumPy array
        img_np = np.array(img)
        gamma = 1.0 / (1.0 + exposure_factor) if exposure_factor >= 0 else 1.0 - exposure_factor

        gamma_table = [np.power(x / 255.0, gamma) * 255.0 for x in range(256)]
        gamma_table = np.round(np.array(gamma_table)).astype(np.uint8)
        adjusted_img = cv2.LUT(img_np, gamma_table)

        adjusted_img = Image.fromarray(adjusted_img)
        
        adjusted_img.save(output_image_path)
        print(output_image_path)

if __name__ == "__main__":
    saturation("berowra-landscape-photography.jpg", "cache/test/000.jpg", 100)
    shadows("berowra-landscape-photography.jpg", "cache/test/001.jpg", -100)
    highlights("berowra-landscape-photography.jpg", "cache/test/002.jpg", 100)
    contrast("berowra-landscape-photography.jpg", "cache/test/003.jpg", -100)
    black("berowra-landscape-photography.jpg", "cache/test/004.jpg", -40)
    white("berowra-landscape-photography.jpg", "cache/test/005.jpg", 100)
    tone("berowra-landscape-photography.jpg", "cache/test/006.jpg", 30)
    color_temperature("berowra-landscape-photography.jpg", "cache/test/007.jpg", 1000)
    exposure("berowra-landscape-photography.jpg", "cache/test/008.jpg", 1)