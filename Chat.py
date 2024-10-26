import base64
import os
import json

from Utils import base64_encode_image


class AgentClient:
    def __init__(self, client, model="gpt-4o-2024-08-06"):
        self.client = client
        self.model = model

    def create_chat_completion(self, model, messages, functions, function_call="auto", max_tokens=1500):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            functions=functions,
            function_call=function_call,
            max_tokens=max_tokens,
        )
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
    def build_messages(system_prompt: str, user_prompt: str = None, image_path: str = None):
        """
        Build a list of messages for a chat system, optionally including a user prompt and an image.

        Parameters:
        system_prompt (str): The system's initial message.
        user_prompt (str, optional): The user's message. Defaults to None.
        image_path (str, optional): The path to an image file to include in the messages. Defaults to None.

        Returns:
        list: A list of messages including the system prompt, user prompt (if provided), and image (if provided).
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        if user_prompt is not None:
            messages.append({"role": "user", "content": user_prompt})
        
        if image_path is not None:
            messages = AgentClient.build_image_message(image_path, messages)
        
        return messages

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

        if completion.choices[0].finish_reason == "function_call":
            function_name = completion.choices[0]["message"]["function_call"]["name"]
            arguments = completion.choices[0]["message"]["function_call"]["arguments"]
            function_args = json.loads(arguments)
            
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
        return None


