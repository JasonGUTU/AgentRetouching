import base64
import os
import json


def base64_encode_image(image_path):
    """
    Encode an image file to a Base64 string.

    Parameters:
    image_path (str): The path to the image file.

    Returns:
    str: The encoded Base64 string.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def pretty_print_content(messages):
    """
    Format and print messages with clear visual hierarchy
    """
    for i, msg in enumerate(messages, 1):
        # Print header
        print(f"\n{'='*80}")
        print(f"Message {i} | Role: {msg['role']}")
        print(f"{'-'*80}")
        
        # Split content into sections based on double newlines
        sections = msg['content'].split('\n\n')
        
        # Print each section with proper formatting
        for section in sections:
            # Handle bullet points and numbered lists
            lines = section.split('\n')
            for line in lines:
                # Add indentation for list items
                if line.strip().startswith(('- ', '   - ', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.')):
                    print('    ' + line.strip())
                else:
                    print(line)
            print()  # Add spacing between sections
        
        print('='*80 + '\n')