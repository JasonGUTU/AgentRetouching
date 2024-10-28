chat_client.agent_interaction(system_prompt=image_content_analyzer_prompt())
chat_client.agent_interaction(system_prompt=global_retouching_concept_prompt())
chat_client.agent_get_plan(system_prompt=retouching_planing_system_prompt(), user_prompt=retouching_planing_user_prompt(image_process.get_function_names()))

while image_process.processing_plan:
    current_function = image_process.processing_plan[0]

    chat_client.agent_execute_plan(
        system_prompt=retouching_execute_system_prompt(),
        user_prompt=retouching_execute_user_prompt(current_function),
        current_function_name=current_function)
    
    image_process.finish_current_plan()