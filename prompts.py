def image_content_analyzer_prompt() -> str:
    prompt = (
        "Carefully observe and describe the scene shown in this photo.\n"
        "No more than 100 words.\n"
        "After analyze, Transfer to the next analyzer."
    )
    return prompt


def image_photo_value_analyzer_prompt() -> str:
    prompt = (
        "Analyze the photographic value of this photo, exploring the unique shooting angle, use of light and shadow, and composition.\n"
        "No more than 100 words."
    )
    return prompt


def image_emo_value_analyzer_prompt() -> str:
    prompt = (
        "Speculate the emotions and artistic values that this painting may convey,\n"
        "and think about the emotions it may evoke and the depth of thought it expresses.\n"
        "No more than 100 words."
    )
    return prompt

