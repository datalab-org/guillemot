from pathlib import Path

from pydantic_ai import BinaryContent


def load_local_image(image_path: str) -> BinaryContent | None:
    """Load a local image file and return BinaryContent"""
    try:
        path = Path(image_path)
        if not path.exists():
            print(f"❌ Image file not found: {image_path}")
            return None

        if not path.is_file():
            print(f"❌ Path is not a file: {image_path}")
            return None

        # Determine media type based on file extension
        extension = path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }

        media_type = media_type_map.get(extension, "image/jpeg")

        # Read the image data
        image_data = path.read_bytes()
        return BinaryContent(data=image_data, media_type=media_type)

    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return None
