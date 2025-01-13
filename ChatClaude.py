import base64
import os
import json

from PIL import Image, ImageEnhance, ExifTags
import anthropic

from Utils import base64_encode_image


class ClaudeAgentClient:
    def __init__(self, api_key, model="claude-3-5-sonnet-20240620", toolbox_instance=None, debug=False):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.debug = debug
        self.toolbox_instance = toolbox_instance
        self.total_tokens = []

    def create_chat_completion(self, messages, tools, tool_choice="required", model=None, max_tokens=None):
        claude_tools = self._convert_openai_tools_to_claude(tools)

        # 检查最后一条消息是否来自 assistant
        # Claude 在使用 tool 时要求最后一条信息不能时是 assistant
        if messages and messages[-1]["role"] == "assistant":
            # 获取工具描述作为用户提示
            tool_description = claude_tools[0].get("description", "Please help process this request.") if claude_tools else "Please help process this request."
            # 添加新的用户消息
            messages = messages + [{"role": "user", "content": tool_description}]
                
        params = {
            "model": model or self.model,
            "messages": self._convert_messages_to_claude_format(messages),
            "tools": claude_tools,
            "tool_choice": {"type": "tool", "name": claude_tools[0].get("name")},
            "max_tokens": max_tokens or 1024,
        }

        if self.debug:
            print(f"Parameters: {json.dumps(params, indent=2, ensure_ascii=False)}")

        # 使用 Claude 的 API 调用方式
        completion = self.client.messages.create(**params)
        
        # 记录 token 使用情况（如果需要的话）
        if hasattr(completion, 'usage') and hasattr(completion.usage, 'total_tokens'):
            self.total_tokens.append(completion.usage.total_tokens)

        return completion
        
            
    def agent_interaction(self, system_prompt, user_prompt=None, provide_image=True, history_messages=True, run_tool=True, histo_image=False):
        """
        Handles the interaction between the agent and the user.
        This is for the conversation without additional function calling, only `func_to_return_responses` is used.

        Args:
            system_prompt (str): The initial system message.
            user_prompt (str, optional): The user's input message. Defaults to None.
            provide_image (bool): Whether to include an image in the interaction. Defaults to True.
            run_tool (bool): Whether to execute a tool based on the completion. Defaults to True.

        Returns:
            If run_tool is False, returns the completion object.
            Otherwise, executes the parsed function call.
        """
        if histo_image:
            image_path = self.toolbox_instance.get_current_histo_image_path()
        else:
            if provide_image:
                image_path = self.toolbox_instance.get_current_image_path()
            else:
                image_path = None

        past_messages = self.toolbox_instance.history_messages if history_messages else None
        messages = self.build_messages(system_prompt, user_prompt, image_path, past_messages)
        completion = self.create_chat_completion(messages, self.toolbox_instance.get_tool_docs([self.toolbox_instance.func_to_return_responses]), tool_choice="required")

        # print(completion.content)
        # print(completion.content[0].input)
        # print(completion.content[0].input['response'])
        
        if run_tool:
            self.parse_function_call(completion, self.toolbox_instance)
            return completion.content[0].input['response']
        else:
            return completion.content[0].input['response']
    
    
    def get_tool_use_response(self, message):
        """
        从 Message 对象的 ToolUseBlock 中提取 input 的 response 值。
        使用动态检查代替类类型判断。
        
        :param message: Message 对象，需包含 content 列表，其中的元素具有 input 属性。
        :return: response 值（字符串），如果未找到 ToolUseBlock 或 response，返回 None。
        """
        # 检查 content 是否为列表
        if not isinstance(message.content, list):
            raise ValueError("message.content 不是列表")
        
        # 遍历 content，查找具有 input 属性的对象
        for item in message.content:
            # 检查是否有 input 属性
            if hasattr(item, 'input') and isinstance(item.input, dict):
                # 获取 input 中的 response
                response = item.input.get('response')
                if response:
                    return response  # 返回 response 值
        
        # 如果未找到符合条件的对象，返回 None
        return None
        
    
    def LLM_interaction(self, system_prompt, user_prompt=None, image_path=None):
        messages = self.build_messages(system_prompt, user_prompt, image_path)
        params = {
            "model": self.model,
            "messages": messages,
        }
        completion = self.client.chat.completions.create(**params)
        return completion.choices[0].message.content
    
    def agent_get_plan(self, system_prompt, user_prompt=None, provide_image=True, history_messages=False, run_tool=True):
        """
        Handles the interaction between the agent and the user to get a processing plan.
        """
        image_path = self.toolbox_instance.get_current_image_path() if provide_image else None
        past_messages = self.toolbox_instance.history_messages if history_messages else None
        messages = self.build_messages(system_prompt, user_prompt, image_path, past_messages)
        completion = self.create_chat_completion(messages, self.toolbox_instance.get_tool_docs([self.toolbox_instance.func_to_get_plan]), tool_choice="required")

        if run_tool:
            self.parse_function_call(completion, self.toolbox_instance)
        else:
            return completion
        
    def agent_get_plan_GUI(self, system_prompt, user_prompt=None, provide_image=True, history_messages=True, run_tool=True):
        """
        Handles the interaction between the agent and the user to get a processing plan.
        """
        image_path = self.toolbox_instance.get_current_image_path() if provide_image else None
        past_messages = self.toolbox_instance.history_messages if history_messages else None
        messages = self.build_messages(system_prompt, user_prompt, image_path, past_messages)
        completion = self.create_chat_completion(messages, self.toolbox_instance.get_tool_docs([self.toolbox_instance.func_to_get_plan_GUI]), tool_choice="required")

        if run_tool:
            self.parse_function_call(completion, self.toolbox_instance)
        else:
            return completion
        
    def agent_execute_plan(self, system_prompt, user_prompt=None, current_function_name=None, provide_image=True, history_messages=True, run_tool=True):
        """
        Handles the interaction between the agent and the user to execute a processing plan.
        """
        image_path = self.toolbox_instance.get_current_image_path() if provide_image else None
        past_messages = self.toolbox_instance.history_messages if history_messages else None
        messages = self.build_messages(system_prompt, user_prompt, image_path, past_messages)
        completion = self.create_chat_completion(messages, self.toolbox_instance.get_tool_docs([getattr(self.toolbox_instance, current_function_name)]), tool_choice="required")

        if run_tool:
            self.parse_function_call(completion, self.toolbox_instance)
        else:
            return completion
        
    def agent_reflection_plan(self, system_prompt, user_prompt=None, current_function_name=None, provide_image=True, history_messages=True, run_tool=True, combine_image=True):
        """
        Handles the interaction between the agent and the user to reflect on a processing plan.
        """

        if combine_image and provide_image:
            image_path_old, image_path_new = self.toolbox_instance.image_paths[0], self.toolbox_instance.get_current_image_path()
            with Image.open(image_path_old) as img1, Image.open(image_path_new) as img2:
                height = min(img1.size[1], img2.size[1])
                width1 = int(img1.size[0] * height / img1.size[1])
                width2 = int(img2.size[0] * height / img2.size[1])
                
                img1 = img1.resize((width1, height))
                img2 = img2.resize((width2, height))
                
                new_img = Image.new('RGB', (width1 + width2, height))
                new_img.paste(img1, (0, 0))
                new_img.paste(img2, (width1, 0))
                
                latest_image = os.path.basename(image_path_new)
                step_number = latest_image.split('_')[0]
                comparison_path = os.path.join(self.toolbox_instance.output_dir_path, f"{step_number}_comparison.jpg")
                new_img.save(comparison_path)
                image_path_new = comparison_path
        else:
            image_path_new = self.toolbox_instance.get_current_image_path() if provide_image else None

        past_messages = self.toolbox_instance.history_messages if history_messages else None
        messages = self.build_messages(system_prompt, user_prompt, image_path_new, past_messages)
        completion = self.create_chat_completion(messages, self.toolbox_instance.get_tool_docs([self.toolbox_instance.satisfactory]), tool_choice="required")

        if run_tool:
            self.parse_function_call(completion, self.toolbox_instance)
        else:
            return completion



    @staticmethod
    def build_image_message(image_path, messages: list = None):
        """
        Build a message containing an image encoded in Base64 format.

        Parameters:
        image_path (str): The path to the image file.
        messages (list, optional): A list of existing messages to append the image message to. Defaults to None.

        Returns:
        list: A list of messages including the image message.
        """
        if messages is None:
            return [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_encode_image(image_path)}",}}]}]
        else:
            if messages[0]["role"] == "system":
                return messages[:1] + [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_encode_image(image_path)}",}}]}] + messages[1:]
            else:
                return [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_encode_image(image_path)}",}}]}] + messages

    @staticmethod
    def build_messages(system_prompt: str, user_prompt: str = None, image_path: str = None, past_messages: list = None):
        """
        Build a list of messages for a chat system, optionally including a user prompt, an image, and past messages.

        Parameters:
        system_prompt (str): The system's initial message.
        user_prompt (str, optional): The user's message. Defaults to None.
        image_path (str, optional): The path to an image file to include in the messages. Defaults to None.
        past_messages (list, optional): A list of previous messages. Defaults to None.

        Returns:
        list: A list of messages including the system prompt, past messages (if provided), 
              user prompt (if provided), and image (if provided).
        """
        messages = [{"role": "system", "content": system_prompt}]

        if past_messages is not None:
            messages.extend(past_messages)
        
        if user_prompt is not None:
            messages.append({"role": "user", "content": user_prompt})
        
        if image_path is not None:
            messages = ClaudeAgentClient.build_image_message(image_path, messages)
        
        return messages


    def _convert_messages_to_claude_format(self, messages):
        """将 OpenAI 格式的消息转换为 Claude 格式"""
        claude_messages = []
        
        for msg in messages:
            content = []
            if isinstance(msg["content"], str):
                content.append({"type": "text", "text": msg["content"]})
            elif isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item.get("type") == "image_url":
                        # 提取 base64 数据
                        base64_data = item["image_url"]["url"].split(",")[1]
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_data
                            }
                        })
                    else:
                        content.append({"type": "text", "text": str(item)})
            
            claude_messages.append({
                "role": "user" if msg["role"] in ["user", "system"] else "assistant",
                "content": content
            })
        
        return claude_messages
    
        

    def _convert_openai_tools_to_claude(self, openai_tools):
        """
        将OpenAI格式的tools转换为Claude格式
        
        Args:
            openai_tools (list): OpenAI格式的tools列表
        
        Returns:
            list: Claude格式的tools列表
        """
        claude_tools = []
        
        for tool in openai_tools:
            if tool["type"] == "function":
                func = tool["function"]
                claude_tool = {
                    "name": func["name"],
                    "description": func.get("description", ""),  # 如果存在description则使用，否则为空字符串
                    "input_schema": {
                        "type": "object",
                        "properties": func["parameters"].get("properties", {}),
                    }
                }
                
                # 如果OpenAI工具定义了required字段，则添加到Claude工具中
                if "required" in func["parameters"]:
                    claude_tool["input_schema"]["required"] = func["parameters"]["required"]
                
                claude_tools.append(claude_tool)
        
        return claude_tools

    @staticmethod
    def parse_function_call(completion, instance):
        """
        Parse and call the function suggested by the API

        Parameters:
        completion (object): The API completion object
        instance (object): The instance of the class `ImageProcessingToolBoxes` to call the method on

        Returns:
        object: The result of the function call
        """
        
        function_mapping = instance.get_function_mapping()
        
        
        # print(function_mapping)
        # print('================== has_name_in_message ===================='*20)
        # print(ClaudeAgentClient.has_name_in_message(completion.content[0], "func_to_get_lightroom_adjustment"))
        # print(completion.content[0].name)
        # print(completion.content[0].input)
        
        
        # if completion.choices[0].finish_reason == "tool_calls":
        # if ClaudeAgentClient.has_name_in_message(completion.content[0], "func_to_get_lightroom_adjustment"):
        try:
            function_name = completion.content[0].name
            arguments = process_dict(completion.content[0].input)
            function_args = arguments
            
            if function_name in function_mapping:
                method_name = function_mapping[function_name]
                if hasattr(instance, method_name):
                    method = getattr(instance, method_name)
                    result = method(**function_args)
                    return result
                else:
                    raise AttributeError(f"The instance does not have a method named '{method_name}'.")
            else:
                raise ValueError(f"The function '{function_name}' is not defined in the function mapping.")
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
        
        
        
def process_dict(input_dict):
    """
    处理字典，将以 '+' 和 '-' 开头的字符串转换为整数或浮点数，其余值保持原样。
    
    :param input_dict: 输入的字典
    :return: 处理后的字典
    """
    output_dict = {}
    
    for key, value in input_dict.items():
        # 如果值是字符串并且以 '+' 开头
        if isinstance(value, str) and (value.startswith('+') or value.startswith('-')):
            try:
                # 转换为浮点数或整数
                if '.' in value:  # 如果是浮点数格式
                    output_dict[key] = float(value)
                else:  # 如果是整数格式
                    output_dict[key] = int(value)
            except ValueError:
                # 如果转换失败，保留为原始字符串
                output_dict[key] = value
        else:
            # 其他情况保持原值
            output_dict[key] = value
    
    return output_dict


        