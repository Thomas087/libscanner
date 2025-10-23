"""
PDF processing utilities with performance benchmarking.
"""

import time
import logging
from typing import Dict, Any
import fitz  # PyMuPDF
import PyPDF2
import io

logger = logging.getLogger(__name__)


def benchmark_pdf_extraction(
    pdf_content: bytes, pdf_url: str = "test"
) -> Dict[str, Any]:
    """
    Benchmark PDF text extraction using both PyMuPDF and PyPDF2.

    Args:
        pdf_content (bytes): PDF content as bytes
        pdf_url (str): URL for logging purposes

    Returns:
        Dict[str, Any]: Benchmark results including timing and text length
    """
    results = {
        "url": pdf_url,
        "content_size": len(pdf_content),
        "pymupdf": {"success": False, "time": 0, "text_length": 0, "error": None},
        "pypdf2": {"success": False, "time": 0, "text_length": 0, "error": None},
    }

    # Test PyMuPDF
    try:
        start_time = time.time()
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text_content = ""

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text_content += page.get_text() + "\n"

        doc.close()
        end_time = time.time()

        results["pymupdf"] = {
            "success": True,
            "time": end_time - start_time,
            "text_length": len(text_content),
            "error": None,
        }

        logger.info(
            f"PyMuPDF: {results['pymupdf']['time']:.3f}s, {results['pymupdf']['text_length']} chars"
        )

    except Exception as e:
        results["pymupdf"]["error"] = str(e)
        logger.warning(f"PyMuPDF failed for {pdf_url}: {e}")

    # Test PyPDF2
    try:
        start_time = time.time()
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_content = ""

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text_content += page.extract_text() + "\n"

        end_time = time.time()

        results["pypdf2"] = {
            "success": True,
            "time": end_time - start_time,
            "text_length": len(text_content),
            "error": None,
        }

        logger.info(
            f"PyPDF2: {results['pypdf2']['time']:.3f}s, {results['pypdf2']['text_length']} chars"
        )

    except Exception as e:
        results["pypdf2"]["error"] = str(e)
        logger.warning(f"PyPDF2 failed for {pdf_url}: {e}")

    # Calculate performance improvement
    if results["pymupdf"]["success"] and results["pypdf2"]["success"]:
        speedup = results["pypdf2"]["time"] / results["pymupdf"]["time"]
        results["speedup"] = speedup
        logger.info(f"PyMuPDF is {speedup:.1f}x faster than PyPDF2")

    return results


def get_pdf_info(pdf_content: bytes) -> Dict[str, Any]:
    """
    Get PDF metadata and information.

    Args:
        pdf_content (bytes): PDF content as bytes

    Returns:
        Dict[str, Any]: PDF information including page count, size, etc.
    """
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")

        info = {
            "page_count": doc.page_count,
            "content_size": len(pdf_content),
            "metadata": doc.metadata,
            "is_encrypted": doc.is_encrypted,
            "needs_pass": doc.needs_pass,
        }

        doc.close()
        return info

    except Exception as e:
        logger.error(f"Error getting PDF info: {e}")
        return {"error": str(e)}
