import os
from mistralai import Mistral
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

def call_mistral_api(prompt, model="mistral-small-2506"):
    """
    Simple function to call Mistral API with a provided prompt.
    
    Args:
        prompt (str): The prompt/question to send to Mistral
        model (str): The Mistral model to use (default: "mistral-small-2506")
    
    Returns:
        str: The response from Mistral API
        
    Raises:
        ValueError: If MISTRAL_API_KEY environment variable is not set
        Exception: If API call fails
    """
    # Get API key from environment variables
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable is not set")
    
    try:
        # Initialize Mistral client
        client = Mistral(api_key=api_key)
        
        # Make the API call
        chat_response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
        )
        
        # Extract and return the response content
        return chat_response.choices[0].message.content
        
    except Exception as e:
        raise Exception(f"Failed to call Mistral API: {str(e)}")


def call_openai_api(prompt, model="gpt-5-nano"):
    """
    Simple function to call OpenAI API with a provided prompt.
    
    Args:
        prompt (str): The prompt/question to send to OpenAI
        model (str): The OpenAI model to use (default: "gpt-5-nano")
    
    Returns:
        str: The response from OpenAI API
        
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
        
        # Make the API call
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
        )
        
        # Extract and return the response content
        return response.choices[0].message.content
        
    except Exception as e:
        raise Exception(f"Failed to call OpenAI API: {str(e)}")


# Create your views here.
