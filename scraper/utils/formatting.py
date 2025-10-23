"""
Formatting utilities for scraper results.
"""


def format_results_pretty(results_by_keyword, keywords):
    """
    Format scraping results in a human-readable way.

    Args:
        results_by_keyword: Dictionary mapping keywords to their results
        keywords: List of keywords that were searched

    Returns:
        str: Formatted string representation of results
    """
    output = []
    output.append("=" * 100)
    output.append("ANIMAL KEYWORDS SCRAPING RESULTS")
    output.append("=" * 100)

    for keyword, data in results_by_keyword.items():
        output.append(f"\n--- KEYWORD: {keyword.upper()} ---")
        output.append(f"Total items found: {data['total_items']}")

        # Show results by prefecture for this keyword
        for prefecture_name, prefecture_data in data['prefectures'].items():
            prefecture = prefecture_data['prefecture']
            results = prefecture_data['results']
            count = prefecture_data['count']

            if count > 0:
                output.append(f"\n  {prefecture['name']} ({prefecture['region']}): {count} items")

                # Show first 3 items as examples
                for i, item in enumerate(results[:3], 1):
                    output.append(f"    Item {i}:")
                    if 'title' in item:
                        output.append(f"      Title: {item['title']}")
                    if 'link' in item:
                        output.append(f"      Link: {item['link']}")
                    if 'description' in item:
                        output.append(f"      Description: {item['description'][:100]}...")

                if len(results) > 3:
                    output.append(f"    ... and {len(results) - 3} more items")
            else:
                output.append(f"\n  {prefecture['name']} ({prefecture['region']}): No results")

    output.append("\n" + "=" * 100)
    return "\n".join(output)
