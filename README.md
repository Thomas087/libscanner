# Libscanner

A Django-based web scraping application that automatically searches and extracts government documents from French prefecture websites, specifically focusing on animal-related regulations and documents.

## What it does

Libscanner is designed to systematically scrape French government websites (prefectures) to find and catalog documents related to animal farming regulations, particularly:

- **Bovin** (cattle)
- **Porcin** (pigs)
- **Volaille** (poultry)
- **Poules** (hens)
- **Pondeuses** (laying hens)
- **Poulets** (chickens)

## Key Features

- **Automated Scraping**: Searches across all French prefecture websites for relevant documents
- **Document Management**: Stores document metadata including title, description, URL, and publication dates
- **ICPE Classification**: Identifies documents related to ICPE (Installations Classées pour la Protection de l'Environnement)
- **Negative Keywords**: Filters out irrelevant documents using configurable negative keywords
- **Task Management**: Uses Celery for background processing with progress tracking
- **PDF Processing**: Extracts text content from PDF documents
- **Admin Interface**: Django admin interface for managing documents and tasks

## Technology Stack

- **Django 5.2.7** - Web framework
- **Celery** - Background task processing
- **Redis** - Message broker and caching
- **Scrapy** - Web scraping framework
- **BeautifulSoup** - HTML parsing
- **PyPDF2/PyMuPDF** - PDF text extraction
- **PostgreSQL** - Database (production)
- **SQLite** - Database (development)

## Project Structure

- `scraper/` - Main Django app containing models, views, and scraping logic
- `libscanner/` - Django project settings and configuration
- `scraper/management/commands/` - Django management commands for running scraping tasks
- `scraper/tasks.py` - Celery task definitions
- `scraper/scraper.py` - Core scraping functionality

## Usage

The application can be used through Django management commands to scrape specific regions or all prefectures for animal-related documents. It provides both a web interface and programmatic access to the scraped data.

## Database Models

- **GovernmentDocument**: Stores scraped documents with metadata
- **NegativeKeyword**: Manages exclusion keywords for filtering
- **ScrapingTask**: Tracks scraping job progress and results
- **ScrapingTaskResult**: Stores detailed results from scraping operations

This tool is particularly useful for researchers, regulatory compliance officers, and agricultural professionals who need to monitor French government regulations related to animal farming.
