#!/usr/bin/env python3
"""
Example usage of OpenAI API integration in the libscanner project.

This script demonstrates how to use the OpenAI API function to generate content.
Make sure to set your OPENAI_API_KEY environment variable before running.
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import the OpenAI function
from llm_api.views import call_openai_api


def main():
    """Example usage of the OpenAI API function."""
    
    # Example 1: Simple bedtime story (as per the documentation example)
    print("=== Example 1: Bedtime Story ===")
    try:
        prompt = "Write a one-sentence bedtime story about a unicorn."
        response = call_openai_api(prompt, model="gpt-4o-mini")
        print(f"Prompt: {prompt}")
        print(f"Response: {response}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Example 2: Different model and prompt
    print("=== Example 2: Creative Writing ===")
    try:
        prompt = "Write a short poem about the ocean in 4 lines."
        response = call_openai_api(prompt, model="gpt-4o-mini")
        print(f"Prompt: {prompt}")
        print(f"Response: {response}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Example 3: Technical question
    print("=== Example 3: Technical Question ===")
    try:
        prompt = "Explain Django's ORM in simple terms."
        response = call_openai_api(prompt, model="gpt-4o-mini")
        print(f"Prompt: {prompt}")
        print(f"Response: {response}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()


if __name__ == "__main__":
    # Check if API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set your OpenAI API key in your .env file or environment variables.")
        sys.exit(1)
    
    print("OpenAI API Example Usage")
    print("=" * 50)
    main()
