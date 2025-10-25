#!/usr/bin/env python
"""
Example usage of the updated scraper with automatic prefecture detection and negative keyword filtering.
"""

from scraper.scraper import scrape_url
from scraper.analysis import scrape_all_results, remove_documents_with_negative_keywords
from scraper.constants import PREFECTURES, get_prefectures_by_region
from scraper.models import NegativeKeyword

# Example 1: Scrape a single prefecture
print("=== Example 1: Scrape Morbihan ===")
results = scrape_url('morbihan.gouv.fr', 'elevage')
print(f"Found {len(results)} documents")

# Example 2: Scrape all results from a prefecture
print("\n=== Example 2: Scrape all results from Morbihan ===")
all_results = scrape_all_results('morbihan.gouv.fr', 'elevage')
print(f"Found {len(all_results)} total documents")

# Example 3: Get prefectures by region
print("\n=== Example 3: Get Bretagne prefectures ===")
bretagne_prefectures = get_prefectures_by_region('Bretagne')
for prefecture in bretagne_prefectures:
    print(f"- {prefecture['name']} ({prefecture['domain']})")

# Example 4: Scrape all prefectures in a region
print("\n=== Example 4: Scrape all Bretagne prefectures ===")
for prefecture in bretagne_prefectures:
    print(f"Scraping {prefecture['name']}...")
    results = scrape_all_results(prefecture['domain'], 'elevage')
    print(f"  Found {len(results)} documents")

# Example 5: Working with negative keywords
print("\n=== Example 5: Working with negative keywords ===")

# Add some negative keywords
negative_keywords = ['test', 'exemple', 'formation']
for keyword in negative_keywords:
    NegativeKeyword.objects.get_or_create(keyword=keyword)
    print(f"Added negative keyword: {keyword}")

# Clean up existing documents with negative keywords
print("Cleaning up documents with negative keywords...")
removed_count = remove_documents_with_negative_keywords()
print(f"Removed {removed_count} documents containing negative keywords")

# List all negative keywords
print("\nCurrent negative keywords:")
for keyword in NegativeKeyword.objects.all():
    print(f"- {keyword}")

print("\n=== Done ===")
