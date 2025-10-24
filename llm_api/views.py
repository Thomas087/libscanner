import os
from typing import Optional, Type, Any
from mistralai import Mistral
from openai import OpenAI
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()


# Example Pydantic models for structured responses
class CalendarEvent(BaseModel):
    """Model for calendar event extraction."""
    name: str
    date: str
    participants: list[str]


class DocumentSummary(BaseModel):
    """Model for document summarization."""
    title: str
    summary: str
    key_points: list[str]
    sentiment: str


class CodeAnalysis(BaseModel):
    """Model for code analysis."""
    language: str
    complexity: str
    issues: list[str]
    suggestions: list[str]

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
