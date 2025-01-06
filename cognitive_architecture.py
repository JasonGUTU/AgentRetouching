from prompts import *
from GUIUtils import *
from GUIToolbox import LightroomGUIToolBox
from Chat import AgentClient


def image_analyze(chat_client, GUIToolbox, global_style="None"):
    _ = chat_client.agent_interaction(
    system_prompt=image_retouching_content_analyzer_and_approaches_thoughts_prompt()
    )
    _ = chat_client.agent_interaction(
    system_prompt=final_retouching_approach_base_on_user_instruction_prompt(global_style)
    )

def make_an_adjustment(chat_client, GUIToolbox):
    histo_style = chat_client.agent_interaction(
        system_prompt=image_histo_analyzer_prompt(),
        histo_image=True
    )
    _ = chat_client.agent_execute_plan(
        system_prompt=retouching_execute_system_prompt(),
        user_prompt=retouching_execute_user_prompt_GUI(),
        current_function_name='func_to_get_lightroom_adjustment'
    )
    _ = chat_client.agent_reflection_plan(
        system_prompt=retouching_reflection_system_prompt_GUI(),
    )

def adjustment_routing_woKI(chat_client, GUIToolbox, global_style="None", retry=5):
    image_analyze(chat_client, GUIToolbox, global_style=global_style)
    count = 1
    while True:
        make_an_adjustment(chat_client, GUIToolbox)
        if GUIToolbox.satisfactory_status:
            break
        count += 1
        if count > retry:
            print("Retouching stoped because of too many retries")
            break