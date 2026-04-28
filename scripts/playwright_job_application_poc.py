"""
Proof-of-concept Playwright automation for a simple job-application form.

Issue reference: validates filling text fields, file uploads, checkbox, submit,
logging, and basic validation handling. Callable from other Python code.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)

FIXTURE_HTML = Path(__file__).resolve().parent / "fixtures" / "sample_job_application_form.html"


def autofill_sample_job_application(
    *,
    resume_path: Optional[Path | str] = None,
    cover_letter_path: Optional[Path | str] = None,
    full_name: str = "Jordan Demo",
    email: str = "jordan.demo@example.com",
    phone: str = "(555) 010-0199",
    form_file_url: Optional[str] = None,
    headless: bool = True,
) -> dict[str, Any]:
    """
    Open the static HTML form (or a custom file:// URL), fill fields, upload files,
    check the agreement box, and submit. Returns a result dict for backend integration.

    If ``resume_path`` / ``cover_letter_path`` are omitted, tiny temp files are used.
    """
    if form_file_url is None:
        if not FIXTURE_HTML.is_file():
            msg = f"Fixture form not found: {FIXTURE_HTML}"
            logger.error(msg)
            return {"ok": False, "error": msg}

    temp_paths: list[Path] = []
    resume = Path(resume_path) if resume_path else _write_temp_file(".pdf", b"%PDF-1.4\n% sample\n", temp_paths)
    cover = Path(cover_letter_path) if cover_letter_path else _write_temp_file(".txt", b"Cover letter sample.\n", temp_paths)

    for label, path in (("resume", resume), ("cover letter", cover)):
        if not path.is_file():
            msg = f"Missing {label} file: {path}"
            logger.error(msg)
            _cleanup_temps(temp_paths)
            return {"ok": False, "error": msg}

    result: dict[str, Any] = {"ok": False}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()

            url = form_file_url or FIXTURE_HTML.as_uri()
            logger.info("Opening %s", url)
            page.goto(url)

            _fill_and_submit(page, full_name, email, phone, resume, cover)

            done = page.locator("#done")
            if done.is_visible():
                logger.info("Form passed client validation and success panel is visible.")
                result["ok"] = True
                result["message"] = "Success: demo form submitted (static page)."
            else:
                result["error"] = "Expected #done to be visible after submit."

            browser.close()
    except Exception as exc:
        logger.exception("Playwright run failed")
        result["error"] = str(exc)
    finally:
        _cleanup_temps(temp_paths)

    return result


def _write_temp_file(suffix: str, data: bytes, temp_paths: list[Path]) -> Path:
    fd, name = tempfile.mkstemp(suffix=suffix)
    path = Path(name)
    path.write_bytes(data)
    temp_paths.append(path)
    return path


def _cleanup_temps(paths: list[Path]) -> None:
    for p in paths:
        try:
            p.unlink(missing_ok=True)  # type: ignore[call-arg]
        except OSError:
            pass


def _fill_and_submit(
    page: Page,
    full_name: str,
    email: str,
    phone: str,
    resume: Path,
    cover: Path,
) -> None:
    """Fill the form; if validation errors appear, log and retry with minimal fixes."""
    page.fill("#fullname", full_name)
    page.fill("#email", email)
    page.fill("#phone", phone)

    page.set_input_files("#resume", str(resume))
    page.set_input_files("#cover", str(cover))

    page.check("#agree")
    page.click('button[type="submit"]')

    if page.locator("#resume-err").is_visible() or page.locator("#cover-err").is_visible():
        logger.warning("Client-side validation reported missing files; re-uploading.")
        page.set_input_files("#resume", str(resume))
        page.set_input_files("#cover", str(cover))
        page.check("#agree")
        page.click('button[type="submit"]')


def run_poc_cli() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out = autofill_sample_job_application()
    if out.get("ok"):
        logger.info("RESULT: %s", out.get("message"))
    else:
        logger.error("RESULT: %s", out.get("error"))


if __name__ == "__main__":
    run_poc_cli()
