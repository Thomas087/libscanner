"""
Data analysis and extraction module for processing scraped government documents.
Contains AI processing, data analysis, and database operations.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import tiktoken
from django.utils import timezone
from pydantic import BaseModel

from .constants import get_prefecture_by_domain
from .models import GovernmentDocument, NegativeKeyword
from .scraper import ScrapedCard, extract_pdf_links_from_page

from llm_api.views import call_openai_api

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Precompiled constants & regex
# ------------------------------------------------------------------------------


DATE_PATTERNS: Tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"Mis à jour le (\d{1,2})/(\d{1,2})/(\d{4})",
        r"Publié le (\d{1,2})/(\d{1,2})/(\d{4})",
        r"Le (\d{1,2})/(\d{1,2})/(\d{4})",
    )
)

# ------------------------------------------------------------------------------
# Multi-document page detection
# ------------------------------------------------------------------------------

def detect_multi_document_page(title: str) -> Optional[str]:
    """
    Detect if a page title indicates it contains multiple documents that need to be scraped separately.
    
    Returns:
        str: The type of multi-document page detected, or None if not a multi-document page.
    """
    if not title:
        return None
    
    title_stripped = title.strip()
    
    # Exact string matches
    exact_matches = {
        "Décisions": "Décisions",
        "Divers": "Divers",
        "Autorisations administratives": "Autorisations administratives",
        "Arrêtés d'autorisation": "Arrêtés d'autorisation",
        "Enregistrement": "Enregistrement",
        "Consultations": "Consultations",
        "Les ICPE soumises à enregistrement": "Les ICPE soumises à enregistrement",
    }
    
    if title_stripped in exact_matches:
        return exact_matches[title_stripped]
    
    # Contains matches
    if "Preuves de dépôt" in title_stripped:
        return "Preuves de dépôt"
    
    if "Preuves de dépôts" in title_stripped:
        return "Preuves de dépôts"
    
    # Year detection (4-digit year, typically 1900-2100)
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    if year_pattern.search(title_stripped):
        # Extract the year for more specific identification
        year_match = year_pattern.search(title_stripped)
        if year_match:
            return f"Year_{year_match.group()}"
    
    return None


# ------------------------------------------------------------------------------
# Keyword checks & date parse
# ------------------------------------------------------------------------------


def parse_date_from_detail(detail_text: str) -> datetime:
    for pat in DATE_PATTERNS:
        m = pat.search(detail_text or "")
        if m:
            day, month, year = m.groups()
            try:
                return datetime(
                    int(year), int(month), int(day), tzinfo=timezone.get_current_timezone()
                )
            except Exception:
                # fall through to now()
                break
    return timezone.now()


# ------------------------------------------------------------------------------
# Negative keyword caching
# ------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _negative_keywords_lower() -> List[str]:
    """
    Load negative keywords using values_list for memory efficiency.
    Only loads keyword strings, not full ORM objects.
    """
    try:
        # Use values_list(flat=True) to get only keyword strings
        return [kw.lower() for kw in NegativeKeyword.objects.values_list('keyword', flat=True) if kw]
    except Exception as e:
        logger.error(f"Error loading negative keywords: {e}")
        return []


def contains_negative_keywords(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    for kw in _negative_keywords_lower():
        if kw and kw in text:
            return True
    return False




# ------------------------------------------------------------------------------
# AI Analysis Functions
# ------------------------------------------------------------------------------

def trim_text(full_page_text: str, max_tokens: int = 200_000, model: str = "gpt-5-nano") -> str:
    """Trim text to fit within a max token limit."""
    # Load the tokenizer for the model you are using
    encoding = tiktoken.encoding_for_model(model)

    # Encode the text into tokens
    tokens = encoding.encode(full_page_text)

    # Truncate if needed
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]

    # Decode back into a string
    trimmed_text = encoding.decode(tokens)
    return trimmed_text


def get_document_info(full_page_text: str) -> str:
    """Get document info using A.I."""
    trimmed_text = trim_text(full_page_text)
    prompt = f"""
    Analyse le texte ci-dessous et renvoie un JSON avec les champs suivants :
    - summary: Un résumé du texte en français (uniquement en français) et en 100 mots maximum.
    - is_animal_project: le booléen indiquant si le texte est lié à un projet d'élevage animal
    - animal_type: le type d'animal (ovin, caprin, bovin, porcin, volaille) si le projet est un projet d'élevage animal, sinon renvoie None
    - animal_number: le nombre d'animaux (nombre) si le projet est un projet d'élevage animal si il est précisé, sinon renvoie None
    Voici le texte à analyser :
    {trimmed_text}"""

    class PrefectureDocumentSummary(BaseModel):
        summary: str
        is_animal_project: bool
        animal_type: Optional[str] = None
        animal_number: Optional[int] = None

    # summary = call_mistral_api(prompt)
    document_info = call_openai_api(prompt, response_format=PrefectureDocumentSummary)
    return document_info


def check_if_intensive_farming(summary: str) -> bool:
    """Check if the project is related to intensive farming based on summary"""
    class IntensiveFarmingCheck(BaseModel):
        is_intensive_farming: bool

    prompt = f"""
    Analyse le texte ci-dessous et renvoie un booléen indiquant si le projet est lié l'élevage intensif d'animaux.
    Le texte est plus suceptible d'être un projet d'élevage intensif d'animaux si il contient des mentions d'élevage animal et certains des mots suivants : Enquête publique , Consultation du public, 3660, Déclaration, Déclaration initiale, Poulets, Cochons, DUC, Poules
    Voici le texte à analyser :
    {summary}"""
    return call_openai_api(prompt, response_format=IntensiveFarmingCheck)


def extract_arretes_prefectoraux_from_page(page_text: str, page_url: str) -> List[ScrapedCard]:
    """
    Extract arrêtés préfectoraux from a multi-document page using AI analysis.
    
    Args:
        page_text: The full text content of the page
        page_url: The URL of the page (used to construct absolute links)
    
    Returns:
        List of ScrapedCard objects representing the extracted arrêtés préfectoraux
    """
    from urllib.parse import urljoin
    
    logger.info(f"[MULTI-DOC] Starting AI extraction of arrêtés préfectoraux from page: {page_url}")
    logger.info(f"[MULTI-DOC] Page text length: {len(page_text)} characters")
    
    trimmed_text = trim_text(page_text, max_tokens=200_000)
    logger.info(f"[MULTI-DOC] Trimmed text length: {len(trimmed_text)} characters (max 200k tokens)")
    
    prompt = f"""
    Analyse le contenu de cette page web qui contient plusieurs arrêtés préfectoraux.
    
    Extrais tous les arrêtés préfectoraux présents sur cette page et renvoie une liste JSON avec pour chaque arrêté :
    - title: Le titre complet de l'arrêté préfectoral (obligatoire, chaîne de caractères)
    - link: L'URL complète (absolue) du lien vers l'arrêté préfectoral. Si le lien est relatif, construis-le à partir de l'URL de base : {page_url} (obligatoire, chaîne de caractères)
    - date_updated: La date de mise à jour ou de publication de l'arrêté au format DD/MM/YYYY. Si la date n'est pas trouvée, utilise la date du jour (obligatoire, chaîne de caractères au format DD/MM/YYYY)
    
    Format JSON attendu :
    {{
        "arretes": [
            {{
                "title": "",
                "link": "",
                "date_updated": ""
            }}
        ]
    }}
    
    Important :
    - Ne renvoie que les arrêtés préfectoraux, pas les autres types de documents
    - Assure-toi que tous les liens sont des URLs absolues complètes (commençant par http:// ou https://)
    - Si un arrêté n'a pas de lien direct, essaie de le construire à partir de l'URL de base : {page_url}
    - Extrais uniquement les informations présentes sur la page, ne crée pas de données fictives
    - Si aucun arrêté préfectoral n'est trouvé, renvoie un tableau vide : {{"arretes": []}}
    
    Voici le contenu de la page à analyser :
    {trimmed_text}
    """
    
    class ArretePrefectoral(BaseModel):
        title: str
        link: str
        date_updated: str
    
    class ArretesList(BaseModel):
        arretes: List[ArretePrefectoral]
    
    try:
        logger.info("[MULTI-DOC] Calling OpenAI API to extract arrêtés préfectoraux...")
        result = call_openai_api(prompt, response_format=ArretesList)
        logger.info(f"[MULTI-DOC] OpenAI API returned {len(result.arretes)} arrêtés préfectoraux")
        
        extracted_arretes = []
        skipped_count = 0
        
        for idx, arrete in enumerate(result.arretes, 1):
            # Validate extracted data
            if not arrete.title or not arrete.title.strip():
                logger.warning(f"[MULTI-DOC] Skipping arrêté #{idx}: empty title")
                skipped_count += 1
                continue
            
            if not arrete.link or not arrete.link.strip():
                logger.warning(f"[MULTI-DOC] Skipping arrêté #{idx} '{arrete.title}': empty link")
                skipped_count += 1
                continue
            
            # Ensure link is absolute
            original_link = arrete.link
            if not arrete.link.startswith('http'):
                arrete.link = urljoin(page_url, arrete.link)
                logger.debug(f"[MULTI-DOC] Converted relative link to absolute: {original_link} -> {arrete.link}")
            
            # Create metadata with date for proper parsing in save_to_database
            metadata = {
                "fr-card__detail": [arrete.date_updated]
            }
            
            # Create a ScrapedCard from the extracted arrêté
            card = ScrapedCard(
                title=arrete.title,
                link=arrete.link,
                description="",
                date_label=arrete.date_updated,
                metadata=metadata,
                html_content=None,
            )
            extracted_arretes.append(card)
            logger.info(f"[MULTI-DOC] Extracted arrêté #{idx}: '{arrete.title}' | Link: {arrete.link} | Date: {arrete.date_updated}")
        
        logger.info(f"[MULTI-DOC] Extraction complete: {len(extracted_arretes)} valid arrêtés extracted, {skipped_count} skipped")
        return extracted_arretes
        
    except Exception as e:
        logger.error(f"[MULTI-DOC] Error extracting arrêtés préfectoraux from page {page_url}: {e}", exc_info=True)
        return []


# ------------------------------------------------------------------------------
# Database Operations
# ------------------------------------------------------------------------------

def save_to_database(scraped_cards: List[ScrapedCard], domain: str, *, now=timezone.now) -> int:
    """
    Persist scraped items with minimal memory usage:
    - Process items one-by-one with immediate DB operations
    - Skip no-op updates
    - Negative keyword filtering
    - Immediate memory cleanup after each item
    """
    import gc
    from .scraper import fetch_page_soup, fetch_page_text, extract_text_from_pdf
    
    if not scraped_cards:
        return 0

    logger.info(f"Processing {len(scraped_cards)} scraped cards for domain: {domain}")

    prefecture_info = get_prefecture_by_domain(domain)
    pref_name = prefecture_info["name"] if prefecture_info else None
    pref_code = prefecture_info["code"] if prefecture_info else None
    region_name = prefecture_info["region"] if prefecture_info else None

    saved = 0
    processed = 0

    for card in scraped_cards:
        try:
            processed += 1
            logger.debug(f"Processing item {processed}/{len(scraped_cards)}: '{card.title}'")

            # Date from metadata if present
            date_updated = now()
            if card.metadata and "fr-card__detail" in card.metadata:
                detail_text = " ".join(card.metadata["fr-card__detail"])
                date_updated = parse_date_from_detail(detail_text)

            # Check negative keywords first (we want to delete records with negative keywords)
            # Query DB for this specific link only
            try:
                existing = GovernmentDocument.objects.filter(link=card.link).only(
                    'id', 'title', 'description', 'date_updated',
                    'prefecture_name', 'prefecture_code', 'region_name'
                ).first()
            except Exception as db_error:
                logger.error(f"Database error while looking up '{card.link}': {db_error}")
                continue

            if contains_negative_keywords(card.title, card.description):
                if existing:
                    logger.info(f"Negative keyword found in existing record, deleting immediately: '{card.title}' - {card.link}")
                    existing.delete()
                else:
                    logger.info(f"Negative keyword found in new record, skipping: '{card.title}'")
                continue

            # Detect multi-document pages
            multi_document_page_type = detect_multi_document_page(card.title)
            contains_multiple_documents = multi_document_page_type is not None
            
            if contains_multiple_documents:
                logger.info(f"[MULTI-DOC] ⚠️  MULTI-DOCUMENT PAGE DETECTED: '{card.title}' (type: {multi_document_page_type}) | URL: {card.link}")

            # Special handling for pages containing multiple documents
            if contains_multiple_documents:
                # Fetch the page content
                from .scraper import fetch_page_text, extract_text_from_pdf
                
                logger.info(f"[MULTI-DOC] Starting special processing for multi-document page: '{card.title}'")
                logger.info(f"[MULTI-DOC] Page URL: {card.link}")
                
                # Get the page text (don't store the page itself)
                is_pdf = card.link.lower().endswith('.pdf')
                page_type = 'PDF' if is_pdf else 'HTML'
                logger.info(f"[MULTI-DOC] Page type: {page_type}")
                
                try:
                    if not is_pdf:
                        logger.info("[MULTI-DOC] Fetching HTML page content...")
                        page_text = fetch_page_text(card.link)
                    else:
                        logger.info("[MULTI-DOC] Extracting text from PDF...")
                        page_text = extract_text_from_pdf(card.link)
                    
                    if not page_text:
                        logger.warning(f"[MULTI-DOC] ❌ Could not extract text from multi-document page: {card.link}")
                        continue
                    
                    logger.info(f"[MULTI-DOC] Successfully extracted {len(page_text)} characters from page")
                    
                except Exception as fetch_error:
                    logger.error(f"[MULTI-DOC] ❌ Error fetching page content from {card.link}: {fetch_error}", exc_info=True)
                    continue
                
                # Extract arrêtés préfectoraux using AI
                logger.info("[MULTI-DOC] Calling AI extraction function...")
                extracted_arretes = extract_arretes_prefectoraux_from_page(page_text, card.link)
                
                if not extracted_arretes:
                    logger.warning(f"[MULTI-DOC] ⚠️  No arrêtés préfectoraux extracted from multi-document page: {card.link}")
                    logger.info("[MULTI-DOC] Skipping multi-document page (no arrêtés found)")
                    continue
                
                logger.info(f"[MULTI-DOC] ✅ Successfully extracted {len(extracted_arretes)} arrêtés préfectoraux")
                logger.info("[MULTI-DOC] Now processing each extracted arrêté as a regular document...")
                
                # Process each extracted arrêté as a regular record
                total_extracted_saved = 0
                for idx, extracted_arrete in enumerate(extracted_arretes, 1):
                    logger.info(f"[MULTI-DOC] Processing extracted arrêté {idx}/{len(extracted_arretes)}: '{extracted_arrete.title}'")
                    # Recursively process each extracted arrêté as a regular card
                    saved_count = save_to_database([extracted_arrete], domain)
                    total_extracted_saved += saved_count
                    logger.info(f"[MULTI-DOC] Extracted arrêté {idx}/{len(extracted_arretes)} processed: {saved_count} record(s) saved")
                
                logger.info(f"[MULTI-DOC] ✅ Multi-document page processing complete: {total_extracted_saved} total records saved from {len(extracted_arretes)} extracted arrêtés")
                logger.info("[MULTI-DOC] Note: The multi-document page itself was NOT stored in the database")
                saved += total_extracted_saved
                
                # Skip normal processing for the multi-document page itself
                continue

            #skip the record if it more than 30 days
            if date_updated < timezone.now() - timedelta(days=30):
                logger.info(f"Skipping record more than 30 days old: '{card.title}' - {card.link}")
                continue

            # Check if record already exists with same link AND date_updated
            if existing and existing.date_updated == date_updated:
                # Record is identical (same link + date_updated), skip it entirely
                logger.info(f"Skipping unchanged record (same link + date): '{card.title}' - {card.link}")
                continue

            # Check if the link is a pdf - if not, fetch the full page text, otherwise extract the text from the pdf
            if not card.link.lower().endswith('.pdf'):
                from .scraper import fetch_page_text
                full_page_text = fetch_page_text(card.link)
            else:
                from .scraper import extract_text_from_pdf
                full_page_text = extract_text_from_pdf(card.link)

            # Generate a summary of the full page text
            document_info = get_document_info(full_page_text)
            summary = document_info.summary
            is_animal_project = document_info.is_animal_project
            animal_type = document_info.animal_type
            animal_number = document_info.animal_number
            logger.info(f"Summary generated for '{card.title}': {summary}")

            if is_animal_project:
                is_intensive_farming = check_if_intensive_farming(summary).is_intensive_farming
                logger.info(f"Intensive farming check result for '{card.title}': {is_intensive_farming}")
            else:
                is_intensive_farming = False

            # If the project is intensive farming, do a more detailed search of document_info
            # by including the PDF contents linked from the detail page and re-run the analysis.
            if is_intensive_farming:
                try:
                    # --- Hard limits for appended PDF text ---
                    PER_PDF_CHAR_LIMIT = 200_000          # cap per PDF text chunk (reasonable upper bound)
                    TOTAL_PDF_CHAR_BUDGET = 400_000       # total budget across all appended PDFs

                    # Collect a few PDF links from the page (dedup + cap)
                    linked_pdfs = extract_pdf_links_from_page(card.link)
                    if linked_pdfs:
                        pdf_sample = []
                        seen = set()
                        for u in linked_pdfs:
                            u_norm = u.strip()
                            if not u_norm or u_norm in seen:
                                continue
                            seen.add(u_norm)
                            pdf_sample.append(u_norm)
                            if len(pdf_sample) >= 3:  # PDF cap limit
                                break

                        # Pull text from those PDFs (skip empties) under strict caps
                        appended_texts: List[str] = []
                        total_appended = 0
                        for pdf_url in pdf_sample:
                            if total_appended >= TOTAL_PDF_CHAR_BUDGET:
                                break
                            try:
                                pdf_text = extract_text_from_pdf(pdf_url)
                                if not pdf_text:
                                    continue
                                # Enforce per-PDF cap
                                if len(pdf_text) > PER_PDF_CHAR_LIMIT:
                                    pdf_text = pdf_text[:PER_PDF_CHAR_LIMIT]
                                # Enforce overall budget
                                remaining = TOTAL_PDF_CHAR_BUDGET - total_appended
                                if remaining <= 0:
                                    break
                                if len(pdf_text) > remaining:
                                    pdf_text = pdf_text[:remaining]

                                appended_texts.append(pdf_text)
                                total_appended += len(pdf_text)
                            except Exception as pdf_err:
                                logger.debug(f"Error extracting appended PDF text from {pdf_url}: {pdf_err}")
                                continue

                        if appended_texts:
                            # Build enriched corpus
                            enriched_text_parts = [
                                "==== PAGE TEXT START ====",
                                full_page_text or "",
                                "==== PAGE TEXT END ====",
                                "==== LINKED PDF TEXT START ====",
                                "\n\n==== NEXT PDF ====\n\n".join(appended_texts),
                                "==== LINKED PDF TEXT END ====",
                            ]
                            enriched_text = "\n\n".join(enriched_text_parts)

                            # Explicitly trim to 200k tokens before analysis
                            enriched_text = trim_text(enriched_text, max_tokens=200_000)

                            # Re-run the same info extraction on the enriched text
                            refined_info = get_document_info(enriched_text)

                            summary = refined_info.summary
                            is_animal_project = bool(refined_info.is_animal_project)
                            animal_type = refined_info.animal_type
                            animal_number = refined_info.animal_number
                            logger.info(
                                f"Refined document info applied for '{card.title}' "
                                f"(animal_project={is_animal_project}, type={animal_type}, n={animal_number})"
                            )
                            
                            # Clear enriched text from memory
                            del enriched_text, enriched_text_parts, appended_texts
                            gc.collect()
                        else:
                            logger.debug(f"No usable PDF text found to enrich '{card.title}'")
                    else:
                        logger.debug(f"No linked PDFs found on page to enrich '{card.title}'")

                except Exception as refine_err:
                    logger.warning(f"Refinement step failed for '{card.title}': {refine_err}")

            if existing:
                # Record exists but has different date_updated or other fields changed
                changed = (
                    existing.title != card.title
                    or (existing.description or "") != (card.description or "")
                    or existing.date_updated != date_updated
                    or (pref_name and existing.prefecture_name != pref_name)
                    or (pref_code and existing.prefecture_code != pref_code)
                    or (region_name and existing.region_name != region_name)
                )
                if changed:
                    logger.info(f"Updating existing record: '{card.title}' - {card.link}")
                    existing.title = card.title
                    existing.description = card.description
                    existing.date_updated = date_updated
                    existing.full_page_text = full_page_text
                    existing.summary = summary
                    existing.is_animal_project = is_animal_project
                    existing.is_intensive_farming = is_intensive_farming
                    if pref_name:
                        existing.prefecture_name = pref_name
                    if pref_code:
                        existing.prefecture_code = pref_code
                    if region_name:
                        existing.region_name = region_name
                    existing.save()
                    saved += 1
                else:
                    logger.debug(f"No changes detected for existing record: '{card.title}'")
            else:
                # Create new record immediately
                logger.info(f"Creating new record: '{card.title}' - {card.link}")
                doc = GovernmentDocument(
                    title=card.title,
                    description=card.description,
                    link=card.link,
                    date_updated=date_updated,
                    full_page_text=full_page_text,
                    summary=summary,
                    is_animal_project=is_animal_project,
                    is_intensive_farming=is_intensive_farming,
                    animal_type=animal_type,
                    animal_number=animal_number,
                    prefecture_name=pref_name,
                    prefecture_code=pref_code,
                    region_name=region_name,
                )
                doc.save()
                saved += 1

            # Clear memory after processing each item
            del full_page_text, summary, document_info
            if 'is_intensive_farming' in locals():
                del is_intensive_farming
            if 'animal_type' in locals():
                del animal_type
            if 'animal_number' in locals():
                del animal_number
            
            # Clear caches periodically to free memory
            if processed % 10 == 0:
                fetch_page_soup.cache_clear()
                fetch_page_text.cache_clear()
                extract_text_from_pdf.cache_clear()
            
            gc.collect()

        except Exception as e:
            logger.error(f"Error processing item '{card.title}': {e}")
            continue

    logger.info(f"Processing complete: {saved} total records saved/updated for {domain}")
    return saved


def remove_documents_with_negative_keywords() -> int:
    """
    Remove ALL documents containing negative keywords.
    Uses iterator() for streaming and bulk delete for efficiency.
    """
    try:
        # Collect IDs to delete in batches
        to_delete_ids = []
        total_removed = 0
        batch_size = 100  # Fixed batch size for bulk operations

        # Remove ALL documents regardless of age
        queryset = GovernmentDocument.objects.all()
        logger.info("Removing ALL documents containing negative keywords")

        # Use iterator() to stream results without loading all into memory
        for d in queryset.iterator(chunk_size=batch_size):
            if contains_negative_keywords(d.title, d.description or ""):
                to_delete_ids.append(d.id)

                # Perform bulk delete when batch is full
                if len(to_delete_ids) >= batch_size:
                    GovernmentDocument.objects.filter(id__in=to_delete_ids).delete()
                    total_removed += len(to_delete_ids)
                    logger.debug(f"Bulk deleted batch of {len(to_delete_ids)} items with negative keywords")
                    to_delete_ids.clear()

        # Delete remaining items
        if to_delete_ids:
            GovernmentDocument.objects.filter(id__in=to_delete_ids).delete()
            total_removed += len(to_delete_ids)
            logger.debug(f"Bulk deleted final batch of {len(to_delete_ids)} items with negative keywords")

        return total_removed
    except Exception as e:
        logger.error(f"Error during negative keyword cleanup: {e}")
        return 0


# ------------------------------------------------------------------------------
# High-level scraping orchestration
# ------------------------------------------------------------------------------

def scrape_all_results(domain: str, keyword: str) -> List[Dict[str, Any]]:
    """
    Scrape all pages, persist results one item at a time with memory cleanup.
    Returns metadata about items (count, sample) instead of all items to reduce memory.

    For backward compatibility, still returns list of dicts but processes items individually.
    """
    from .scraper import iterate_search_pages, fetch_page_soup, fetch_page_text, extract_text_from_pdf
    import gc
    
    logger.info("=" * 80)
    logger.info(f"Starting full scrape for domain: {domain}, keyword: '{keyword}'")
    logger.info("=" * 80)

    total_saved = 0
    total_count = 0

    for page in iterate_search_pages(domain, keyword):
        total_count += len(page)
        logger.debug(f"Processing page with {len(page)} items, total scraped so far: {total_count}")

        # Process each item individually
        for item in page:
            logger.debug(f"Processing individual item: '{item.title}'")
            saved_count = save_to_database([item], domain)
            total_saved += saved_count
            
            # Clear memory after each item
            del item
            
            # Clear caches periodically to free memory
            if total_count % 20 == 0:
                fetch_page_soup.cache_clear()
                fetch_page_text.cache_clear()
                extract_text_from_pdf.cache_clear()
            
            gc.collect()
            
            logger.debug(f"Progress: {total_saved} total items saved/updated so far")

    logger.info("Running cleanup of negative keywords...")
    removed_count = remove_documents_with_negative_keywords()
    if removed_count:
        logger.info(f"Cleanup complete: removed {removed_count} documents with negative keywords")
    else:
        logger.info("Cleanup complete: no documents with negative keywords found")

    logger.info("=" * 80)
    logger.info(f"SCRAPING COMPLETE for {domain}/{keyword}")
    logger.info(f"Total scraped: {total_count} items | Total saved/updated: {total_saved} items")
    logger.info("=" * 80)

    # Return summary instead of full data to save memory
    # For backward compatibility, return empty list (data is already in DB)
    return []
