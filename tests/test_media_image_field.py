from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile

from shop.admin.forms import MediaImageField, MediaAssetAdminForm


def create_png_file():
    buffer = BytesIO()

    Image.new("RGB", (1, 1)).save(buffer, format="PNG")

    return SimpleUploadedFile(
        "image.png",
        buffer.getvalue(),
        content_type="image/png",
    )


def test_media_image_field_accepts_valid_svg():
    uploaded_file = SimpleUploadedFile(
        "icon.svg",
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        b'<circle cx="5" cy="5" r="4"/>'
        b"</svg>",
        content_type="image/svg+xml",
    )

    field = MediaImageField(required=False)

    result = field.clean(uploaded_file)

    assert result is uploaded_file
    assert result.tell() == 0


def test_media_image_field_rejects_malformed_svg():
    uploaded_file = SimpleUploadedFile(
        "broken.svg",
        b"<svg><circle></svg>",
        content_type="image/svg+xml",
    )

    field = MediaImageField(required=False)

    with pytest.raises(forms.ValidationError):
        field.clean(uploaded_file)


def test_media_image_field_rejects_non_svg_xml():
    uploaded_file = SimpleUploadedFile(
        "fake.svg",
        b"<document><text>Hello</text></document>",
        content_type="image/svg+xml",
    )

    field = MediaImageField(required=False)

    with pytest.raises(forms.ValidationError):
        field.clean(uploaded_file)


def test_media_image_field_accepts_valid_png():
    uploaded_file = create_png_file()
    field = MediaImageField(required=False)

    result = field.clean(uploaded_file)

    assert result is uploaded_file
    assert result.tell() == 0


def test_media_image_field_rejects_fake_image():
    uploaded_file = SimpleUploadedFile(
        "fake.png",
        b"this is not an image",
        content_type="image/png",
    )

    field = MediaImageField(required=False)

    with pytest.raises(forms.ValidationError):
        field.clean(uploaded_file)


def test_media_image_field_allows_empty_value():
    field = MediaImageField(required=False)

    assert field.clean(None) is None


@patch("shop.admin.forms.upload_image_to_cloudinary")
def test_media_asset_admin_form_accepts_svg(mock_upload):
    mock_upload.return_value = {
        "secure_url": ("https://res.cloudinary.com/test/image/upload/icon.svg"),
        "public_id": "zoony/product-images/icon",
    }

    uploaded_file = SimpleUploadedFile(
        "icon.svg",
        b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
        content_type="image/svg+xml",
    )

    form = MediaAssetAdminForm(
        data={
            "title": "Test icon",
            "alt_text": "Test icon",
            "source": "manual",
            "is_active": True,
        },
        files={
            "upload_file": uploaded_file,
        },
    )

    assert form.is_valid(), form.errors
    assert (
        form.cleaned_data["image_url"]
        == "https://res.cloudinary.com/test/image/upload/icon.svg"
    )
    assert form.cleaned_data["cloudinary_public_id"] == "zoony/product-images/icon"

    mock_upload.assert_called_once()
