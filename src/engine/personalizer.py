import os
import re
import html
from typing import Dict, Any, Tuple
from config.settings import settings
from src.crm.schemas import Lead
from src.engine.spintax import SpintaxParser
from src.tracker.pixel_generator import PixelGenerator

class Personalizer:
    """
    Renders personalized email pitches by injecting lead-specific variables,
    evaluating spintax variations, and building multipart plain/HTML bodies.
    """

    DEFAULT_TRACK_NAME = "Midnight Reverie"
    DEFAULT_STREAM_LINK = "https://open.spotify.com/artist/kxrn-gupta"
    DEFAULT_BIO_LINK = "https://kxrn.is-a.dev/press"

    @classmethod
    def load_template(cls, template_path: str) -> str:
        """Loads a raw template file."""
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found at: {template_path}")
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    @classmethod
    def build_context(
        cls,
        lead: Lead,
        extra_vars: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Builds variable substitution dictionary with safe fallbacks."""
        extra = extra_vars or {}

        # Fallback for publication
        publication = (lead.publication or "").strip()
        if not publication or publication.lower() == "your platform":
            publication = "your platform"

        # Fallback for recent work
        recent_article = (lead.recent_work or "").strip()
        if not recent_article:
            recent_article = "the latest independent music releases"

        context = {
            "First_Name": lead.first_name,
            "Full_Name": lead.name,
            "Publication": publication,
            "Recent_Article": recent_article,
            "Track_Name": extra.get("track_name", cls.DEFAULT_TRACK_NAME),
            "Stream_Link": extra.get("stream_link", cls.DEFAULT_STREAM_LINK),
            "Artist_Bio_Link": extra.get("bio_link", cls.DEFAULT_BIO_LINK),
            "Sender_Name": settings.sender_name,
            "Sender_Email": settings.sender_email,
            "Original_Subject": extra.get("original_subject", f"{cls.DEFAULT_TRACK_NAME} - Kxrn Gupta"),
        }
        return context

    @classmethod
    def render(
        cls,
        template_str: str,
        lead: Lead,
        extra_vars: Dict[str, Any] = None,
        inject_pixel: bool = True
    ) -> Tuple[str, str, str]:
        """
        Renders (subject, text_content, html_content).
        """
        context = cls.build_context(lead, extra_vars)

        # 1. Variable substitution ({{Var}})
        rendered = template_str
        for key, val in context.items():
            pattern = re.compile(rf"\{{\{{\s*{re.escape(key)}\s*\}}\}}", re.IGNORECASE)
            rendered = pattern.sub(str(val), rendered)

        # 2. Spintax evaluation
        rendered = SpintaxParser.spin(rendered)

        # 3. Extract Subject if present
        subject = f"{context['Track_Name']} - Kxrn Gupta"
        body_lines = []
        lines = rendered.splitlines()

        for idx, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            else:
                body_lines.append(line)

        body_text = "\n".join(body_lines).strip()

        # 4. Generate HTML version
        html_body = cls._text_to_html(body_text)

        # 5. Inject 1x1 tracking pixel
        if inject_pixel and lead.id:
            pixel_tag = PixelGenerator.get_pixel_tag(lead.id)
            html_body += f"\n<br>\n{pixel_tag}"

        return subject, body_text, html_body

    @staticmethod
    def _text_to_html(text: str) -> str:
        """Converts formatted text with markdown-like links & bolding into clean HTML."""
        # Escape raw HTML
        escaped = html.escape(text)

        # Bold **text**
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

        # Links: [text](url)
        escaped = re.sub(
            r"\[([^\]]+)\]\((https?://[^\)]+)\)",
            r'<a href="\2" style="color: #2563eb; text-decoration: underline;" target="_blank">\1</a>',
            escaped
        )

        # Auto-link raw URLs: https://...
        escaped = re.sub(
            r'(?<!href=")(https?://[^\s<]+)',
            r'<a href="\1" style="color: #2563eb; text-decoration: underline;" target="_blank">\1</a>',
            escaped
        )

        # Convert double newlines to paragraph tags, single newlines to <br>
        paragraphs = escaped.split("\n\n")
        html_paragraphs = []
        for p in paragraphs:
            p_clean = p.strip().replace("\n", "<br>")
            if p_clean:
                html_paragraphs.append(f'<p style="margin: 0 0 14px 0; line-height: 1.6; color: #1e293b; font-size: 15px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif;">{p_clean}</p>')

        return f'<div style="max-width: 600px; margin: 0 auto; padding: 12px 0;">\n' + "\n".join(html_paragraphs) + "\n</div>"
