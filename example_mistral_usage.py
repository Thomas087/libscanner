#!/usr/bin/env python
"""
Example usage of the Mistral API function from other apps.

This file demonstrates how to import and use the call_mistral_api function
from the llm_api app in other parts of your Django project.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append('/Users/thomasgraziani/Library/Mobile Documents/com~apple~CloudDocs/Documents/Libscanner/libscanner')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'libscanner.settings')
django.setup()

# Now you can import from your Django apps
from llm_api.views import call_mistral_api


def example_usage():
    """
    Example of how to use the call_mistral_api function.
    """
    try:
        # Example 1: Simple question
        prompt = "What is the best French cheese?"
        response = call_mistral_api(prompt)
        print(f"Question: {prompt}")
        print(f"Response: {response}")
        print("-" * 50)
        
        # Example 2: Using a different model
        prompt2 = "Explain quantum computing in simple terms."
        response2 = call_mistral_api(prompt2, model="mistral-small-latest")
        print(f"Question: {prompt2}")
        print(f"Response: {response2}")
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure to set the MISTRAL_API_KEY environment variable")
    except Exception as e:
        print(f"API call failed: {e}")


if __name__ == "__main__":
    example_usage()
