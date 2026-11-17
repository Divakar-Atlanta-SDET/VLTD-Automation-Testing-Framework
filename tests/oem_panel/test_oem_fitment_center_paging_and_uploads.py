"""
OEM > Management > User Management > Fitment Center: paging, sorting and file uploads.

Paging: the list shows 10 centres a page (no page-size control) with First / Previous / Go to page N / Next / Last and
"Showing 1 to 10 of N results"; the API takes `page` and `per_page` (1 to 100). Sorting: the column headers are not sortable on the
screen, the list is always newest first; the API sorts by created_at, updated_at, short_name (fitment code) and owner_name.

Uploads: the premises image (JPG, PNG or WEBP, up to 5 MB, 300 to 4096 pixels a side) and, when a GST number is entered, a PDF
GST certificate (up to 2 MB). Only harmless generated files are used (text, empty files, small images, padded or random bytes).
Every request that tests the server carries a deliberately wrong pincode, so even a server that skipped a file rule could not
create or change a centre: the test looks for the error on the file field.
"""

import math
import re

import pytest
from playwright.sync_api import Page, expect

from pages.oem_panel.fitment_centers import FitmentCenterDetailsPage, FitmentCenterFormPage, FitmentCenterListPage
from utils.api_client import ApiClient
from utils.file_utils import (
    GIF_1X1, JPEG_1X1, SVG_TEXT, TEST_PDF, WEBP_1X1, create_oversized_pdf, create_oversized_png, create_sized_png, large_png_bytes,
    noise_png_bytes, png_bytes, write_file,
)
from utils.oem_panel_api import FITMENT_CENTRES, edit_fitment_centre, fitment_centre, fitment_centre_fields

pytestmark = [pytest.mark.oem_panel, pytest.mark.xdist_group("oem-devices")]

PAGE_SIZE = 10


def _page(oem_api: ApiClient, query: str = "") -> dict:
    return oem_api.get(f"{FITMENT_CENTRES}?{query}").json()


def _need_several_pages(oem_api: ApiClient) -> int:
    total = _page(oem_api)["summary"]["total"]
    if total <= PAGE_SIZE:
        pytest.skip(f"The OEM has {total} fitment centres; paging needs more than {PAGE_SIZE}")
    return total


# ── Paging (screen) ───────────────────────────────────────────────────────────

def test_the_pager_walks_through_every_centre(oem_page: Page, oem_api: ApiClient) -> None:
    total = _need_several_pages(oem_api)
    pages = math.ceil(total / PAGE_SIZE)
    everything = [fc["short_name"] for fc in _page(oem_api, "per_page=100")["data"]]
    listing = FitmentCenterListPage(oem_page).open()

    expect(listing.pager_summary).to_have_text(f"Showing 1 to {PAGE_SIZE} of {total} results")
    expect(listing.pager_button("First page")).to_be_disabled()  # nothing before the first page
    expect(listing.pager_button("Previous page")).to_be_disabled()
    seen = listing.codes()
    assert len(seen) == PAGE_SIZE

    for number in range(2, pages + 1):
        listing.go_to("Next page")
        last = min(number * PAGE_SIZE, total)
        expect(listing.pager_summary).to_have_text(f"Showing {(number - 1) * PAGE_SIZE + 1} to {last} of {total} results")
        seen += listing.codes()

    expect(listing.pager_button("Next page")).to_be_disabled()  # nothing after the last page
    expect(listing.pager_button("Last page")).to_be_disabled()
    assert sorted(seen) == sorted(everything)  # every centre exactly once

    listing.go_to("First page")
    expect(listing.pager_summary).to_have_text(f"Showing 1 to {PAGE_SIZE} of {total} results")
    listing.go_to("Last page")
    expect(listing.pager_summary).to_have_text(f"Showing {(pages - 1) * PAGE_SIZE + 1} to {total} of {total} results")
    listing.go_to("Go to page 1")
    expect(listing.pager_summary).to_have_text(f"Showing 1 to {PAGE_SIZE} of {total} results")


def test_the_list_shows_the_newest_centre_first(oem_page: Page, oem_api: ApiClient) -> None:
    expected = [fc["short_name"] for fc in _page(oem_api)["data"]]  # the API default: created_at, newest first
    listing = FitmentCenterListPage(oem_page).open()

    assert listing.codes() == expected


def test_applying_a_filter_goes_back_to_the_first_page(oem_page: Page, oem_api: ApiClient) -> None:
    _need_several_pages(oem_api)
    listing = FitmentCenterListPage(oem_page).open()
    listing.go_to("Next page")
    expect(listing.pager_button("Previous page")).to_be_enabled()  # now on page 2

    listing.choose_status("Blacklisted")

    expected = [fc["short_name"] for fc in _page(oem_api, "status=blacklisted")["data"]]
    expect(oem_page.get_by_role("row").nth(1)).to_contain_text(f"Code: {expected[0]}")
    assert listing.codes() == expected  # page 1 of the blacklisted centres


# ── Paging and sorting (API) ──────────────────────────────────────────────────

@pytest.mark.parametrize("per_page", [3, 7, 10])
def test_every_centre_is_on_exactly_one_page(oem_api: ApiClient, per_page: int) -> None:
    total = _page(oem_api)["summary"]["total"]
    ids, number = [], 1
    while True:
        body = _page(oem_api, f"per_page={per_page}&page={number}")
        meta = body["meta"]
        assert (meta["current_page"], meta["per_page"], meta["total"]) == (number, per_page, total)
        assert meta["last_page"] == math.ceil(total / per_page)
        assert meta["from"] == (number - 1) * per_page + 1 and meta["to"] == (number - 1) * per_page + len(body["data"])
        ids += [fc["id"] for fc in body["data"]]
        if number >= meta["last_page"]:
            break
        number += 1
    assert len(ids) == total == len(set(ids)), "a centre is missing or listed twice across the pages"


def test_a_page_beyond_the_last_is_empty(oem_api: ApiClient) -> None:
    last = _page(oem_api, "per_page=5")["meta"]["last_page"]

    body = _page(oem_api, f"per_page=5&page={last + 1}")

    assert body["data"] == [] and body["meta"]["total"] == _page(oem_api)["summary"]["total"]


@pytest.mark.parametrize("query", ["per_page=0", "per_page=101", "per_page=abc", "sort_by=password", "sort_by=business_name", "sort_dir=up"])
def test_the_server_refuses_invalid_paging_and_sorting(oem_api: ApiClient, query: str) -> None:
    response = oem_api.get(f"{FITMENT_CENTRES}?{query}")

    assert response.status == 422, f"{query}: {response.status} {response.text()[:200]}"
    assert response.json()["errors"]


SORT_KEYS = {
    "created_at": lambda fc: fc["created_at"],
    "updated_at": lambda fc: fc["updated_at"],
    "short_name": lambda fc: fc["short_name"].casefold(),
    "owner_name": lambda fc: fc["owner_name"].casefold(),
}


@pytest.mark.parametrize("direction", ["asc", "desc"])
@pytest.mark.parametrize("sort_by", SORT_KEYS)
def test_the_api_sorts_in_the_requested_direction(oem_api: ApiClient, sort_by: str, direction: str) -> None:
    rows = _page(oem_api, f"per_page=100&sort_by={sort_by}&sort_dir={direction}")["data"]

    keys = [SORT_KEYS[sort_by](fc) for fc in rows]

    assert len(rows) > 1 and keys == sorted(keys, reverse=direction == "desc"), keys


def test_sorting_and_a_filter_work_together(oem_api: ApiClient) -> None:
    rows = _page(oem_api, "per_page=100&status=blacklisted&sort_by=short_name&sort_dir=asc")["data"]

    assert rows and {fc["status"] for fc in rows} == {"blacklisted"}
    keys = [fc["short_name"].casefold() for fc in rows]
    assert keys == sorted(keys)


# ── The premises image (screen; nothing is submitted) ─────────────────────────

UNREADABLE = "Unable to read the selected image"
WRONG_TYPE = "Please upload a JPG, PNG or WEBP image"

IMAGE_REFUSALS = {
    "299-px-square": (lambda d: create_sized_png(d, 299, "small.png"), "Image dimensions must be at least 300 × 300 pixels"),
    "4097-px-square": (lambda d: write_file(d, "huge.png", large_png_bytes(4097, 4097)), "Image dimensions must not exceed 4096 × 4096 pixels"),
    "300-by-5000": (lambda d: create_sized_png(d, 300, "tall.png", height=5000), "Image dimensions must not exceed 4096 × 4096 pixels"),
    "text-called-png": (lambda d: write_file(d, "fake.png", "this is not an image"), UNREADABLE),
    "empty-png": (lambda d: write_file(d, "empty.png", b""), UNREADABLE),
    "html-called-png": (lambda d: write_file(d, "page.png", "<html><script>alert(1)</script></html>"), UNREADABLE),
    "text-file": (lambda d: write_file(d, "note.txt", "hello"), WRONG_TYPE),
    "pdf": (lambda d: write_file(d, "doc.pdf", TEST_PDF.read_bytes()), WRONG_TYPE),
    "gif": (lambda d: write_file(d, "a.gif", GIF_1X1), WRONG_TYPE),
    "svg": (lambda d: write_file(d, "a.svg", SVG_TEXT), WRONG_TYPE),
    "png-with-exe-name": (lambda d: write_file(d, "photo.png.exe", png_bytes(320)), WRONG_TYPE),
    "over-5-mb": (lambda d: create_oversized_png(d, 6 * 1024 * 1024, "big.png"), "Image size must not exceed 5 MB"),
}


@pytest.mark.parametrize("build, message", IMAGE_REFUSALS.values(), ids=IMAGE_REFUSALS.keys())
def test_the_form_refuses_an_unsuitable_image_and_sends_nothing(oem_page: Page, tmp_path, build, message: str) -> None:
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "POST" and "/fitment-centres" in r.url else None)
    form = FitmentCenterFormPage(oem_page).open_new()

    form.image_input.set_input_files(build(tmp_path))

    expect(form.error(message)).to_be_visible()
    assert not sent


@pytest.mark.parametrize("width, height", [(300, 300), (320, 600)], ids=["smallest-allowed", "not-square"])
def test_the_form_accepts_a_suitable_image(oem_page: Page, tmp_path, width: int, height: int) -> None:
    form = FitmentCenterFormPage(oem_page).open_new()

    form.image_input.set_input_files(create_sized_png(tmp_path, width, "photo.png", height=height))

    expect(form.main.get_by_text("photo.png")).to_be_visible()
    for message in (UNREADABLE, WRONG_TYPE, "Image size must not exceed 5 MB"):
        expect(form.error(message)).to_have_count(0)
    expect(form.error(re.compile(r"Image dimensions must"))).to_have_count(0)


# ── The GST certificate (screen; the edit form of the lifecycle centre, never submitted with a file) ──

def _edit_form_with_gst(oem_page: Page, lifecycle: dict) -> FitmentCenterFormPage:
    oem_page.goto(f"/oem/users/fitment-centers/{lifecycle['id']}/edit")
    form = FitmentCenterFormPage(oem_page, edit=True).wait_until_loaded()
    form.gst_box.fill("07AAAAA0000A1Z5")
    expect(form.certificate_input).to_have_count(1)  # a GST number makes the certificate mandatory
    return form


def test_a_gst_number_needs_a_certificate(oem_page: Page, lifecycle: dict) -> None:
    sent = []
    oem_page.on("request", lambda r: sent.append(r) if r.method == "POST" and "/fitment-centres/" in r.url else None)
    form = _edit_form_with_gst(oem_page, lifecycle)

    form.submit()

    expect(form.error("GST Certificate is required when GST Number is added or changed")).to_be_visible()
    assert not sent


@pytest.mark.parametrize(
    "build, message",
    [
        (lambda d: write_file(d, "cert.txt", "hello"), "GST Certificate must be a PDF file"),
        (lambda d: create_sized_png(d, 320, "cert.png"), "GST Certificate must be a PDF file"),
        (lambda d: create_oversized_pdf(d, 3 * 1024 * 1024, "big.pdf"), "GST Certificate must not exceed 2 MB"),
    ],
    ids=["text-file", "image", "over-2-mb"],
)
def test_the_form_refuses_an_unsuitable_gst_certificate(oem_page: Page, lifecycle: dict, tmp_path, build, message: str) -> None:
    form = _edit_form_with_gst(oem_page, lifecycle)

    form.certificate_input.set_input_files(build(tmp_path))

    expect(form.error(message)).to_be_visible()


# ── The server checks the files itself (API) ──────────────────────────────────

def _png_part(name: str = "a.png", mime: str = "image/png", content: bytes | None = None) -> dict:
    return {"name": name, "mimeType": mime, "buffer": png_bytes(320) if content is None else content}


def _pdf_part(name: str = "c.pdf", mime: str = "application/pdf", content: bytes | None = None) -> dict:
    return {"name": name, "mimeType": mime, "buffer": TEST_PDF.read_bytes() if content is None else content}


BAD_IMAGES = {
    "text-called-png": lambda: _png_part("fake.png", content=b"this is not an image"),
    "empty-png": lambda: _png_part("empty.png", content=b""),
    "html-called-png": lambda: _png_part("x.png", content=b"<html><script>alert(1)</script></html>"),
    "svg": lambda: _png_part("a.svg", "image/svg+xml", SVG_TEXT.encode()),
    "gif": lambda: _png_part("a.gif", "image/gif", GIF_1X1),
    "pdf": lambda: _png_part("a.pdf", "application/pdf", TEST_PDF.read_bytes()),
    "299-px": lambda: _png_part("small.png", content=png_bytes(299)),
    "4097-px": lambda: _png_part("huge.png", content=large_png_bytes(4097, 4097)),
    "over-5-mb": lambda: _png_part("big.png", content=noise_png_bytes(1500, 1500)),  # a real PNG of 6.4 MB
}
BAD_CERTIFICATES = {
    "text-called-pdf": lambda: _pdf_part("fake.pdf", content=b"not a pdf"),
    "empty-pdf": lambda: _pdf_part("empty.pdf", content=b""),
    "html-called-pdf": lambda: _pdf_part("x.pdf", content=b"<html><script>alert(1)</script></html>"),
    "image": lambda: _pdf_part("c.png", "image/png", png_bytes(320)),
    "text-file": lambda: _pdf_part("c.txt", "text/plain", b"hello"),
    "over-2-mb": lambda: _pdf_part("big.pdf", content=b"%PDF-1.4\n" + b"0" * (3 * 1024 * 1024)),
}


def _register_that_cannot_succeed(oem_api: ApiClient, **parts):
    """A registration with a wrong pincode: the server answers 422 whatever the files are, and reports every field it checked."""
    return oem_api.request("POST", FITMENT_CENTRES, multipart={**fitment_centre_fields(oem_api, pincode="11000a"), "fitment_centre_image": _png_part(), **parts})


def _edit_that_cannot_succeed(oem_api: ApiClient, fc: dict, **parts):
    return edit_fitment_centre(oem_api, fc, pincode="11000a", **parts)


def _errors(response) -> dict:
    assert response.status == 422, f"{response.status} {response.text()[:300]}"
    return response.json()["errors"]


@pytest.mark.parametrize("make", BAD_IMAGES.values(), ids=BAD_IMAGES.keys())
def test_the_server_refuses_an_unsuitable_image(oem_api: ApiClient, lifecycle: dict, make) -> None:
    total = _page(oem_api)["summary"]["total"]

    registration = _errors(_register_that_cannot_succeed(oem_api, fitment_centre_image=make()))
    edit = _errors(_edit_that_cannot_succeed(oem_api, lifecycle, fitment_centre_image=make()))

    assert "fitment_centre_image" in registration, registration
    assert "fitment_centre_image" in edit, edit
    assert _page(oem_api)["summary"]["total"] == total
    assert fitment_centre(oem_api, lifecycle["id"])["image_url"] == lifecycle["image_url"]


def test_the_server_checks_a_suitable_image_only_for_the_wrong_pincode(oem_api: ApiClient, lifecycle: dict) -> None:
    """The control of the tests above: with a good image the file field is not reported, so those errors do come from the file."""
    registration = _errors(_register_that_cannot_succeed(oem_api))
    edit = _errors(_edit_that_cannot_succeed(oem_api, lifecycle))

    assert set(registration) == {"pincode"} and set(edit) == {"pincode"}


@pytest.mark.parametrize("name, mime, content", [("a.jpg", "image/jpeg", JPEG_1X1), ("a.webp", "image/webp", WEBP_1X1)], ids=["jpeg", "webp"])
def test_the_server_accepts_jpeg_and_webp_as_image_types(oem_api: ApiClient, name: str, mime: str, content: bytes) -> None:
    """A 1 x 1 file is refused for its size only, which proves the format itself is allowed."""
    errors = _errors(_register_that_cannot_succeed(oem_api, fitment_centre_image={"name": name, "mimeType": mime, "buffer": content}))

    assert "dimensions" in errors["fitment_centre_image"][0], errors["fitment_centre_image"]


@pytest.mark.parametrize("make", BAD_CERTIFICATES.values(), ids=BAD_CERTIFICATES.keys())
def test_the_server_refuses_an_unsuitable_gst_certificate(oem_api: ApiClient, lifecycle: dict, make) -> None:
    gst = {"gst_number": "07AAAAA0000A1Z5"}

    registration = _errors(_register_that_cannot_succeed(oem_api, **gst, gst_certificate=make()))
    edit = _errors(_edit_that_cannot_succeed(oem_api, lifecycle, **gst, gst_certificate=make()))

    assert "gst_certificate" in registration and "gst_certificate" in edit, (registration, edit)
    assert fitment_centre(oem_api, lifecycle["id"])["gst_number"] == lifecycle["gst_number"]


def test_the_server_requires_a_certificate_with_a_gst_number_and_accepts_a_pdf(oem_api: ApiClient, lifecycle: dict) -> None:
    without = _errors(_register_that_cannot_succeed(oem_api, gst_number="07AAAAA0000A1Z5"))
    with_pdf = _errors(_register_that_cannot_succeed(oem_api, gst_number="07AAAAA0000A1Z5", gst_certificate=_pdf_part()))

    assert "gst_certificate" in without
    assert "gst_certificate" not in with_pdf


# ── Known defect ──────────────────────────────────────────────────────────────

@pytest.mark.xfail(
    reason="BUG-057: the premises image is never shown: the API sends http://<ip>:8087/... and the https page blocks it as mixed content",
    strict=False,
)
def test_the_premises_image_is_shown_on_the_details_page(oem_page: Page, lifecycle: dict) -> None:
    details = FitmentCenterDetailsPage(oem_page).open_id(lifecycle["id"])

    expect(details.main.get_by_text("Image unavailable")).to_have_count(0)
    oem_page.wait_for_function("() => [...document.querySelectorAll('main img')].some(img => img.complete && img.naturalWidth > 0)", timeout=5_000)  # a loaded picture
