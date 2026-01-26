import os
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()


def call_openai_api(prompt, model="gpt-5-nano", response_format=None, system_message=None):
    """
    Function to call OpenAI API with optional structured response support.
    
    Args:
        prompt (str): The prompt/question to send to OpenAI
        model (str): The OpenAI model to use (default: "gpt-5-nano")
        response_format (BaseModel, optional): Pydantic model for structured response
        system_message (str, optional): System message to provide context
    
    Returns:
        str or BaseModel: The response from OpenAI API (text or parsed structured data)
        
    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
        Exception: If API call fails
    """
    # Get API key from environment variables
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Prepare messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare API call parameters
        api_params = {
            "model": model,
            "messages": messages,
        }
        
        # Add response format if provided
        if response_format:
            api_params["response_format"] = response_format
        
        # Make the API call
        if response_format:
            # Use structured response parsing
            response = client.chat.completions.parse(**api_params)
            return response.choices[0].message.parsed
        else:
            # Use regular text response
            response = client.chat.completions.create(**api_params)
            return response.choices[0].message.content
        
    except Exception as e:
        raise Exception(f"Failed to call OpenAI API: {str(e)}")


# Create your views here.
