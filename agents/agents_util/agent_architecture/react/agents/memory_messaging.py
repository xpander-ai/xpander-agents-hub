import copy
import json

import yaml


class MemoryMessaging:
    def __init__(self):
        self._messages = []

    def add_message(self, message: str, message_prefix: str = ""):
        self._messages.append(message_prefix + message)

    def get_messages(self):
        return copy.deepcopy(self._messages)

    def save(self, file_name: str, file_type: str):
        if file_type not in ["txt", "yaml", "json"]:
            raise ValueError("Unsupported file type. Choose from 'txt', 'yaml', or 'json'.")

        with open(file_name, 'w') as file:
            if file_type == "txt":
                for message in self._messages:
                    file.write(message + "\n")
            elif file_type == "yaml":
                yaml.dump(self._messages, file)
            elif file_type == "json":
                json.dump(self._messages, file, indent=4)
