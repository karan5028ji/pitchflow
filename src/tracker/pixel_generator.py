from config.settings import settings

class PixelGenerator:
    """
    Generates invisible 1x1 image tracking pixel tags and URLs.
    """

    @staticmethod
    def get_pixel_url(lead_id: str) -> str:
        """Constructs the absolute URL for the 1x1 tracking pixel."""
        base = settings.tracking_server_url.rstrip("/")
        return f"{base}/t/{lead_id}.png"

    @classmethod
    def get_pixel_tag(cls, lead_id: str) -> str:
        """
        Returns the HTML img tag to embed at the bottom of the email.
        Uses inline styles to prevent email clients from displaying borders or empty boxes.
        """
        url = cls.get_pixel_url(lead_id)
        return (
            f'<img src="{url}" alt="" width="1" height="1" '
            f'style="display:none !important; min-height:1px !important; '
            f'width:1px !important; border:0 !important; outline:0 !important;" />'
        )
