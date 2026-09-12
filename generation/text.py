from html import escape


def fit_text_to_html_limit(text, max_escaped_length):
    """Trim plain text so its escaped representation fits Telegram."""

    cleaned = "\n\n".join(
        " ".join(paragraph.split())
        for paragraph in (text or "").splitlines()
        if paragraph.strip()
    )

    if not cleaned or max_escaped_length <= 0:
        return ""

    if len(escape(cleaned)) <= max_escaped_length:
        return cleaned

    ellipsis = "…"
    available = max_escaped_length - len(ellipsis)
    low, high = 0, len(cleaned)

    while low < high:
        middle = (low + high + 1) // 2

        if len(escape(cleaned[:middle])) <= available:
            low = middle
        else:
            high = middle - 1

    candidate = cleaned[:low].rstrip()
    word_end = max(candidate.rfind(" "), candidate.rfind("\n"))

    if word_end > 0:
        candidate = candidate[:word_end].rstrip()

    return f"{candidate}{ellipsis}" if candidate else ""

