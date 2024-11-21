import logging

from colorama import Fore, Style


class Logger:

    MAX_RESPONSE_LENGTH = 1000

    COLOR_MAP = {
        "RED": Fore.RED,
        "GREEN": Fore.GREEN,
        "YELLOW": Fore.YELLOW,
        "BLUE": Fore.BLUE,
        "MAGENTA": Fore.MAGENTA,
        "CYAN": Fore.CYAN,
        "WHITE": Fore.WHITE
    }

    def __init__(self, color: str, logger_name, level=logging.INFO):
        # Use a unique logger name based on the agent type
        logger = logging.getLogger(f"{logger_name}")
        logger.setLevel(level)

        # Map the string color to Fore color
        color = self.COLOR_MAP.get(color.upper(), Fore.WHITE)

        # Create console handler with a specific color
        ch = logging.StreamHandler()
        ch.setLevel(level)

        formatter = logging.Formatter(f'{color}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Style.RESET_ALL}')
        ch.setFormatter(formatter)

        # Adding the handler to the logger
        if not logger.handlers:
            logger.addHandler(ch)
        self.logger = logger
        self.logger.propagate = False

    def log_xpander_tool_results(self, tool_response, selected_operation, selected_params, url,
                                 max_length: int = MAX_RESPONSE_LENGTH):
        log_tool = tool_response[:max_length] + "..." if len(
            tool_response) > max_length else tool_response

        log_messages = [
            f"Selected Tool: {selected_operation}",
            f"Path url: {url}",
            f"Payload: {selected_params}",
            f"Tool Response: {log_tool}"
        ]

        for message in log_messages:
            self.logger.info(message)

        return log_messages
