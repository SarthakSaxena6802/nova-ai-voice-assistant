"""Allow-list of websites Nova may open. Natural language can only select a key from this
table – it can never produce an arbitrary URL or shell command."""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Website:
    key: str
    name: str
    url: str
    aliases: tuple[str, ...] = ()


SAFE_WEBSITES: dict[str, Website] = {
    w.key: w
    for w in [
        Website("google", "Google", "https://www.google.com", ("google search", "the browser")),
        Website("youtube", "YouTube", "https://www.youtube.com", ("you tube", "yt")),
        Website("github", "GitHub", "https://github.com", ("git hub", "the github page")),
        Website("gmail", "Gmail", "https://mail.google.com", ("my email", "my mail", "email", "g mail", "mail")),
        Website("spotify", "Spotify", "https://open.spotify.com", ("spotty fy",)),
        Website("wikipedia", "Wikipedia", "https://www.wikipedia.org", ("wiki",)),
        Website("stackoverflow", "Stack Overflow", "https://stackoverflow.com", ("stack overflow",)),
        Website("linkedin", "LinkedIn", "https://www.linkedin.com", ("linked in",)),
        Website("reddit", "Reddit", "https://www.reddit.com", ("read it",)),
        Website("maps", "Google Maps", "https://maps.google.com", ("google maps", "maps")),
        Website("drive", "Google Drive", "https://drive.google.com", ("google drive", "drive")),
        Website("calendar", "Google Calendar", "https://calendar.google.com", ("google calendar", "my calendar", "calendar")),
        Website("news", "Google News", "https://news.google.com", ("google news", "news")),
        Website("amazon", "Amazon", "https://www.amazon.com", ()),
        Website("netflix", "Netflix", "https://www.netflix.com", ()),
        Website("twitter", "X (Twitter)", "https://x.com", ("twitter",)),
        Website("outlook", "Outlook", "https://outlook.live.com", ()),
        Website("chatgpt", "ChatGPT", "https://chatgpt.com", ("chat gpt",)),
        Website("claude", "Claude", "https://claude.ai", ("claude ai",)),
    ]
}


def is_allowed_url(url: str) -> bool:
    return any(url == w.url for w in SAFE_WEBSITES.values())


def find_website(text: str) -> Website | None:
    """Match the longest alias/key mentioned in *text*; fall back to fuzzy matching
    individual words to tolerate transcription errors ("githab", "youtub")."""
    padded = f" {re.sub(r'[^a-z0-9 ]', ' ', text.lower())} "
    padded = padded.replace(" dot com ", " ").replace(".com", " ")
    candidates: list[tuple[int, Website]] = []
    for site in SAFE_WEBSITES.values():
        for phrase in (site.key, site.name.lower(), *site.aliases):
            if f" {phrase} " in padded:
                candidates.append((len(phrase), site))
    if candidates:
        return max(candidates, key=lambda c: c[0])[1]

    words = [w for w in padded.split() if len(w) >= 4]
    joined = [a + b for a, b in zip(words, words[1:])]
    for word in words + joined:
        match = difflib.get_close_matches(word, list(SAFE_WEBSITES), n=1, cutoff=0.8)
        if match:
            return SAFE_WEBSITES[match[0]]
    return None
