import cloudinary
import cloudinary.uploader
cloudinary.config()

cloudinary.config(
    cloud_name="dttdhu04k",
    api_key="626686491772271",
    api_secret="-ZDnupK8QKpqCLbGlhEH9CV1434",
    secure=True,
)


class UploadedImage:
    """
    Represents an uploaded image with its URL, public ID, and format.
    """

    def __init__(self, url: str, public_id: str, format: str, file_type: str = "image"):
        self.url = url
        self.public_id = public_id
        self.format = format
        self.type = file_type

    def __repr__(self):
        return f"UploadedImage(url={self.url}, public_id={self.public_id}, format={self.format})"


def upload(
    file,
):
    """
    Uploads an image to Cloudinary and returns the URL.
    """
    response = cloudinary.uploader.upload(file, resource_type="auto")
    return UploadedImage(
        url=response.get("secure_url"),
        public_id=response.get("public_id"),
        format=response.get("format"),
        
    )


def upload_large(file, type: str = "image"):
    """
    Uploads a large image to Cloudinary and returns the URL.
    """
    response = cloudinary.uploader.upload_large(file, resource_type=type)
    return UploadedImage(
        url=response.get("secure_url"),
        public_id=response.get("public_id"),
        format=response.get("format"),
        file_type=type,
    )


def delete_file(public_id: str):
    """Deletes an image from Cloudinary using its public ID."""
    response = cloudinary.uploader.destroy(public_id)
    if response.get("result") == "ok":
        return True
    return False
