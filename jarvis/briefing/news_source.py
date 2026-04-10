"""Fetch news from RSS feeds."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import NewsConfig


@dataclass
class NewsItem:
    title: str
    link: str
    source: str


def fetch_news(cfg: NewsConfig) -> list[NewsItem]:
    """Fetch headlines from configured RSS feeds."""
    try:
        import feedparser
    except ImportError:
        return [NewsItem(title="feedparser not installed", link="", source="")]

    items = []
    for feed_url in cfg.feeds:
        try:
            feed = feedparser.parse(feed_url)
            source = feed.feed.get("title", feed_url)
            for entry in feed.entries[: cfg.max_items_per_feed]:
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    link=entry.get("link", ""),
                    source=source,
                ))
        except Exception:
            continue
    return items
