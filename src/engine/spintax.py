import random
import re

class SpintaxParser:
    """
    Parses and expands spintax strings (e.g., '{Hey|Hi|Hello} {there|friend}').
    Supports nested spintax patterns like '{A|{B|C}}'.
    """

    SPINTAX_REGEX = re.compile(r"\{([^{}]+)\}")

    @classmethod
    def spin(cls, text: str) -> str:
        """
        Recursively resolves all innermost {option1|option2|...} blocks
        until no curly braces with pipes remain.
        """
        if not text:
            return ""

        while True:
            match = cls.SPINTAX_REGEX.search(text)
            if not match:
                break
            options = match.group(1).split("|")
            chosen = random.choice(options)
            # Replace only this occurrence
            text = text[:match.start()] + chosen + text[match.end():]

        return text
