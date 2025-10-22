"""
Django management command to test PDF processing performance.
"""

from django.core.management.base import BaseCommand, CommandError
from scraper.pdf_utils import benchmark_pdf_extraction, get_pdf_info
import requests


class Command(BaseCommand):
    help = "Test PDF processing performance with PyMuPDF vs PyPDF2"

    def add_arguments(self, parser):
        parser.add_argument("--url", type=str, help="PDF URL to test (optional)")
        parser.add_argument(
            "--file", type=str, help="Local PDF file path to test (optional)"
        )
        parser.add_argument(
            "--iterations",
            type=int,
            default=3,
            help="Number of iterations to run (default: 3)",
        )

    def handle(self, *args, **options):
        url = options.get("url")
        file_path = options.get("file")
        iterations = options.get("iterations", 3)

        if not url and not file_path:
            # Use a default test PDF URL
            url = "https://www.morbihan.gouv.fr/contenu/telechargement/78286/607946/file/Présentation%20conférences%20Paysage%20et%20Agriculture%20en%20DDTM%20du%20Morbihan%20-%20Octobre%202025.pdf"
            self.stdout.write(f"Using default test PDF: {url}")

        try:
            if url:
                self.test_pdf_url(url, iterations)
            elif file_path:
                self.test_pdf_file(file_path, iterations)

        except Exception as e:
            raise CommandError(f"Error testing PDF performance: {e}")

    def test_pdf_url(self, url: str, iterations: int):
        """Test PDF processing performance from URL."""
        self.stdout.write(f"Testing PDF performance from URL: {url}")
        self.stdout.write("=" * 60)

        try:
            # Download PDF content
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            pdf_content = response.content
            self.stdout.write(f"Downloaded PDF: {len(pdf_content)} bytes")

            # Get PDF info
            info = get_pdf_info(pdf_content)
            if "error" not in info:
                self.stdout.write("PDF Info:")
                self.stdout.write(f"  Pages: {info.get('page_count', 'Unknown')}")
                self.stdout.write(
                    f"  Size: {info.get('content_size', 'Unknown')} bytes"
                )
                self.stdout.write(f"  Encrypted: {info.get('is_encrypted', 'Unknown')}")

            # Run benchmark
            self.stdout.write(f"\nRunning {iterations} iterations...")

            total_pymupdf_time = 0
            total_pypdf2_time = 0
            successful_pymupdf = 0
            successful_pypdf2 = 0

            for i in range(iterations):
                self.stdout.write(f"\nIteration {i + 1}/{iterations}:")

                results = benchmark_pdf_extraction(pdf_content, url)

                if results["pymupdf"]["success"]:
                    total_pymupdf_time += results["pymupdf"]["time"]
                    successful_pymupdf += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  PyMuPDF: {results['pymupdf']['time']:.3f}s, {results['pymupdf']['text_length']} chars"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  PyMuPDF: FAILED - {results['pymupdf']['error']}"
                        )
                    )

                if results["pypdf2"]["success"]:
                    total_pypdf2_time += results["pypdf2"]["time"]
                    successful_pypdf2 += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  PyPDF2:  {results['pypdf2']['time']:.3f}s, {results['pypdf2']['text_length']} chars"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  PyPDF2:  FAILED - {results['pypdf2']['error']}"
                        )
                    )

                if "speedup" in results:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Speedup: {results['speedup']:.1f}x faster"
                        )
                    )

            # Summary
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("PERFORMANCE SUMMARY")
            self.stdout.write("=" * 60)

            if successful_pymupdf > 0:
                avg_pymupdf = total_pymupdf_time / successful_pymupdf
                self.stdout.write(
                    f"PyMuPDF average: {avg_pymupdf:.3f}s ({successful_pymupdf}/{iterations} successful)"
                )
            else:
                self.stdout.write("PyMuPDF: No successful runs")

            if successful_pypdf2 > 0:
                avg_pypdf2 = total_pypdf2_time / successful_pypdf2
                self.stdout.write(
                    f"PyPDF2 average:  {avg_pypdf2:.3f}s ({successful_pypdf2}/{iterations} successful)"
                )
            else:
                self.stdout.write("PyPDF2: No successful runs")

            if successful_pymupdf > 0 and successful_pypdf2 > 0:
                overall_speedup = (total_pypdf2_time / successful_pypdf2) / (
                    total_pymupdf_time / successful_pymupdf
                )
                self.stdout.write(
                    f"Overall speedup: {overall_speedup:.1f}x faster with PyMuPDF"
                )

                if overall_speedup > 2:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "✓ Significant performance improvement with PyMuPDF"
                        )
                    )
                elif overall_speedup > 1.5:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "✓ Good performance improvement with PyMuPDF"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠ Modest performance improvement with PyMuPDF"
                        )
                    )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error testing PDF URL: {e}"))

    def test_pdf_file(self, file_path: str, iterations: int):
        """Test PDF processing performance from local file."""
        self.stdout.write(f"Testing PDF performance from file: {file_path}")
        self.stdout.write("=" * 60)

        try:
            with open(file_path, "rb") as f:
                pdf_content = f.read()

            self.stdout.write(f"Loaded PDF: {len(pdf_content)} bytes")

            # Run the same benchmark as URL test
            # (Implementation would be similar to test_pdf_url but with local file)
            self.stdout.write(
                "Local file testing not yet implemented. Use --url instead."
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error testing PDF file: {e}"))
