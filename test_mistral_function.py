#!/usr/bin/env python
"""
Simple test script to verify the Mistral API function works correctly.
This script tests the function without making actual API calls.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append('/Users/thomasgraziani/Library/Mobile Documents/com~apple~CloudDocs/Documents/Libscanner/libscanner')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'libscanner.settings')
django.setup()

from llm_api.views import call_mistral_api


def test_function_import():
    """Test that the function can be imported correctly."""
    print("✓ Function imported successfully")


def test_missing_api_key():
    """Test error handling when API key is missing."""
    # Temporarily remove API key if it exists
    original_key = os.environ.get("MISTRAL_API_KEY")
    if "MISTRAL_API_KEY" in os.environ:
        del os.environ["MISTRAL_API_KEY"]
    
    try:
        call_mistral_api("test prompt")
        print("✗ Should have raised ValueError for missing API key")
    except ValueError as e:
        if "MISTRAL_API_KEY environment variable is not set" in str(e):
            print("✓ Correctly raises ValueError for missing API key")
        else:
            print(f"✗ Unexpected ValueError: {e}")
    except Exception as e:
        print(f"✗ Unexpected exception: {e}")
    finally:
        # Restore original API key if it existed
        if original_key:
            os.environ["MISTRAL_API_KEY"] = original_key


def test_function_signature():
    """Test that the function has the correct signature."""
    import inspect
    
    sig = inspect.signature(call_mistral_api)
    params = list(sig.parameters.keys())
    
    expected_params = ['prompt', 'model']
    if params == expected_params:
        print("✓ Function has correct signature")
    else:
        print(f"✗ Function signature incorrect. Expected {expected_params}, got {params}")


def main():
    """Run all tests."""
    print("Testing Mistral API function...")
    print("=" * 40)
    
    test_function_import()
    test_missing_api_key()
    test_function_signature()
    
    print("=" * 40)
    print("Test completed!")
    print("\nTo test with actual API calls, set MISTRAL_API_KEY environment variable and run:")
    print("python example_mistral_usage.py")


if __name__ == "__main__":
    main()
