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

# Import the OpenAI function and example models
from llm_api.views import call_openai_api, CalendarEvent, DocumentSummary, CodeAnalysis


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
    
    # Example 4: Structured Response - Calendar Event (as per documentation)
    print("=== Example 4: Structured Response - Calendar Event ===")
    try:
        prompt = "Alice and Bob are going to a science fair on Friday."
        system_message = "Extract the event information."
        event = call_openai_api(
            prompt=prompt,
            model="gpt-4o-mini",
            response_format=CalendarEvent,
            system_message=system_message
        )
        print(f"Prompt: {prompt}")
        print(f"System: {system_message}")
        print(f"Structured Response:")
        print(f"  Name: {event.name}")
        print(f"  Date: {event.date}")
        print(f"  Participants: {event.participants}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Example 5: Structured Response - Document Summary
    print("=== Example 5: Structured Response - Document Summary ===")
    try:
        prompt = "Summarize this article: 'The Future of AI in Healthcare: A comprehensive look at how artificial intelligence is revolutionizing medical diagnosis, treatment planning, and patient care. Key benefits include improved accuracy, reduced costs, and better patient outcomes. However, challenges remain in data privacy, regulatory compliance, and ensuring equitable access to AI-powered healthcare solutions.'"
        system_message = "Analyze and summarize the document with key points and sentiment."
        summary = call_openai_api(
            prompt=prompt,
            model="gpt-4o-mini",
            response_format=DocumentSummary,
            system_message=system_message
        )
        print(f"Prompt: {prompt[:100]}...")
        print(f"System: {system_message}")
        print(f"Structured Response:")
        print(f"  Title: {summary.title}")
        print(f"  Summary: {summary.summary}")
        print(f"  Key Points: {summary.key_points}")
        print(f"  Sentiment: {summary.sentiment}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Example 6: Structured Response - Code Analysis
    print("=== Example 6: Structured Response - Code Analysis ===")
    try:
        prompt = "Analyze this Python code: def fibonacci(n): if n <= 1: return n; return fibonacci(n-1) + fibonacci(n-2)"
        system_message = "Analyze the code for language, complexity, issues, and provide suggestions."
        analysis = call_openai_api(
            prompt=prompt,
            model="gpt-4o-mini",
            response_format=CodeAnalysis,
            system_message=system_message
        )
        print(f"Prompt: {prompt}")
        print(f"System: {system_message}")
        print(f"Structured Response:")
        print(f"  Language: {analysis.language}")
        print(f"  Complexity: {analysis.complexity}")
        print(f"  Issues: {analysis.issues}")
        print(f"  Suggestions: {analysis.suggestions}")
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
