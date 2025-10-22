# Prefecture Data Management

This document explains how to manage prefecture data in the Libscanner project.

## Overview

The project uses a simple constants-based approach to store French prefecture data including regions and government domains. This data is used to systematically scrape government websites across different prefectures.

## Data Storage

### Static Constants (Recommended approach)

- **Location**: `scraper/constants.py`
- **Use case**: Static data that doesn't change often
- **Benefits**: Fast access, no database queries, simple to maintain
- **Usage**: Import and use directly in your code

## Usage Examples

### Using Static Constants

```python
from scraper.constants import PREFECTURES, get_prefectures_by_region, get_all_domains

# Get all prefectures
all_prefectures = PREFECTURES

# Get prefectures by region
bretagne_prefectures = get_prefectures_by_region('Bretagne')

# Get all domains
all_domains = get_all_domains()
```

## Management Commands

### 1. Scrape All Prefectures

```bash
python manage.py scrape_all_prefectures --keyword elevage
```

### 2. Scrape Specific Region

```bash
python manage.py scrape_all_prefectures --keyword elevage --region Bretagne
```

### 3. Scrape Specific Prefecture

```bash
python manage.py scrape_all_prefectures --keyword elevage --prefecture Morbihan
```

### 4. List Available Data

```bash
# List all regions
python manage.py scrape_all_prefectures --list-regions

# List all prefectures
python manage.py scrape_all_prefectures --list-prefectures
```

## Adding New Prefectures

### Method 1: Update Constants File

1. Edit `scraper/constants.py`
2. Add new prefecture to the `PREFECTURES` list:

```python
{
    'name': 'New Prefecture',
    'region': 'New Region',
    'domain': 'new-prefecture.gouv.fr',
    'code': '99'
}
```

### Method 2: Programmatically

```python
from scraper.constants import PREFECTURES

# Add to the PREFECTURES list
PREFECTURES.append({
    'name': 'New Prefecture',
    'region': 'New Region',
    'domain': 'new-prefecture.gouv.fr',
    'code': '99'
})
```

## File Structure

```
scraper/
├── constants.py              # Prefecture data and helper functions
├── management/
│   └── commands/
│       ├── scrape_morbihan.py           # Scrape single prefecture
│       └── scrape_all_prefectures.py    # Scrape all prefectures
└── scraper.py                # Updated with constants import
```

## Best Practices

1. **Keep constants simple** - Only add data that's truly static
2. **Use helper functions** - Leverage the provided utility functions
3. **Test scraping** with a small subset before running on all prefectures
4. **Update constants** when new prefectures are added

## Troubleshooting

- **Import errors**: Ensure all imports are correct in your management commands
- **Scraping failures**: Check that domains are correct and accessible
- **Data consistency**: Make sure all prefecture entries have required fields (name, region, domain, code)
