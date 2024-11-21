import importlib
import inspect
from typing import Any, Dict

def route_tool_call(name: str, parameters: Dict[str, Any]) -> Any:
    """
    Routes a tool call to the appropriate function based on the function name and parameters.
    
    Parameters:
        name (str): The name of the function to call (e.g., 'crunchbase_autocomplete')
        parameters (Dict[str, Any]): The parameters to pass to the function
        
    Returns:
        Any: The result of the function call
        
    Raises:
        ImportError: If the module cannot be imported
        AttributeError: If the function cannot be found in the module
        Exception: If there's an error executing the function
    """
    try:
        # Split the function name to get the module name (e.g., 'crunchbase' from 'crunchbase_autocomplete')
        module_name = name.split('__')[0].lower()
        
        # Import the corresponding module dynamically
        module = importlib.import_module(f"without_xpander.tools.{module_name}")
        function_name = name.split('__')[1].lower()
        # Get the function from the module
        function = getattr(module, function_name)
        
        # Get the function's signature
        sig = inspect.signature(function)
        
        # Filter out parameters that aren't in the function signature
        valid_params = {
            k: v for k, v in parameters.items() 
            if k in sig.parameters
        }
        
        # Call the function with the parameters
        result = function(**valid_params)
        return result
        
    except ImportError as e:
        raise ImportError(f"Could not import module for function {name}: {str(e)}")
    except AttributeError as e:
        raise AttributeError(f"Function {name} not found: {str(e)}")
    except Exception as e:
        raise Exception(f"Error executing function {name}: {str(e)}")