#!/usr/bin/env python3
"""Refresh realtors.json for MarkhamRealtor.com.

Production mode uses the Serper Maps API as the discovery/data-ingestion layer.
Local development falls back to a deterministic seed dataset so the entire site
can be built and tested without credentials.

The script intentionally does not scrape regulator registries, Google Maps HTML,
review websites, or MLS data directly. Any optional crawl of an agent's own
website is limited to its home page and respects robots.txt.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "realtors.json"
SERPER_ENDPOINT = "https://google.serper.dev/maps"
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
REQUIRE_LIVE_DATA = os.getenv("REQUIRE_LIVE_DATA", "0") == "1"
USER_AGENT = "MarkhamRealtorBot/1.0 (+https://markhamrealtor.com/)"
REQUEST_TIMEOUT = 12
TOP_LIMIT = 10
MINIMUM_LIVE_RESULTS = 5

MARKHAM_FSAS = {
    "L3P", "L3R", "L3S", "L3T", "L6B", "L6C", "L6E", "L6G"
}

DISCOVERY_QUERIES = (
    "realtor in Markham Ontario",
    "real estate agent in Markham Ontario",
    "real estate broker in Markham Ontario",
    "realtor in Unionville Ontario",
)

SPECIALTY_KEYWORDS = {
    "Luxury": ("luxury", "estate homes", "high-end", "high end"),
    "Condos": ("condo", "condominium"),
    "First-time Buyers": ("first time buyer", "first-time buyer"),
    "Investors": ("investor", "investment property"),
    "Sellers": ("seller", "listing agent", "home selling", "sell your home"),
    "Buyers": ("buyer", "buy a home", "home buying"),
    "Pre-construction": ("pre-construction", "preconstruction", "new construction"),
    "Commercial": ("commercial real estate", "commercial property", "industrial", "retail"),
    "Relocation": ("relocation", "relocating"),
    "Downsizing": ("downsizing", "downsizer", "senior move"),
}

BROKERAGE_BRANDS = (
    "RE/MAX",
    "CENTURY 21",
    "Royal LePage",
    "Homelife",
    "HomeLife",
    "Bay Street",
    "T-One Group Realty",
    "Carefree Home Sold Realty",
    "Sutton",
    "Keller Williams",
    "eXp Realty",
    "Right at Home Realty",
    "Forest Hill Real Estate",
)

MOCK_SOURCE_DATA: list[dict[str, Any]] = [
    {
        "title": "RE/MAX Benczik Kavanagh Real Estate Team",
        "address": "120 Main Street Markham N, Markham, ON L3P 1Y1",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 218,
        "website": "https://www.bkteam.ca/",
        "phoneNumber": "+1 905-477-7766",
        "category": "Real estate agent",
        "position": 1,
        "brokerage": "RE/MAX All-Stars Benczik Kavanagh Team Realty",
        "specialties": ["Markham", "Residential", "Sellers", "Buyers"],
    },
    {
        "title": "The ONE Team",
        "address": "3601 Highway 7 E, Suite 908, Markham, ON L3R 0M3",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 205,
        "website": "https://theoneteam.ca/",
        "category": "Real estate agent",
        "position": 2,
        "brokerage": "CENTURY 21 The ONE Realty, Brokerage",
        "specialties": ["Markham", "Residential", "Sellers", "Buyers"],
    },
    {
        "title": "Pris Han",
        "address": "8920 Woodbine Ave, Suite 206, Markham, ON L3R 9W9",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 138,
        "website": "https://hanhomesoldrealty.com/en/",
        "phoneNumber": "+1 647-360-8963",
        "category": "Real estate agent",
        "position": 3,
        "brokerage": "Carefree Home Sold Realty Inc., Brokerage",
        "specialties": ["Markham", "Residential", "Sellers", "Buyers"],
    },
    {
        "title": "Jacky Wu Realtor",
        "address": "50 Cathedral High St, Unit 1, Markham, ON L6C 0N9",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 111,
        "website": "https://www.jackywurealtor.com/",
        "phoneNumber": "+1 647-968-5899",
        "category": "Real estate agent",
        "position": 4,
        "brokerage": "T-One Group Realty Inc., Brokerage",
        "specialties": ["Markham", "Residential", "Sellers", "Buyers"],
    },
    {
        "title": "Jodh Toor",
        "address": "7780 Woodbine Ave, Suite 15, Markham, ON L3R 2N7",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 108,
        "website": "https://www.google.com/maps/search/?api=1&query=Jodh+Toor+Century+21+Markham+Ontario",
        "phoneNumber": "+1 647-526-2455",
        "category": "Real estate agent",
        "position": 5,
        "brokerage": "CENTURY 21",
        "specialties": ["Markham", "Residential", "Sellers", "Buyers"],
    },
    {
        "title": "Antonio Saade",
        "address": "165 Main Street Markham N, Markham, ON L3P 1Y2",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 106,
        "website": "https://www.antoniosaade.ca/",
        "phoneNumber": "+1 647-297-1112",
        "category": "Real estate broker",
        "position": 6,
        "brokerage": "CENTURY 21 Leading Edge Realty Inc., Brokerage",
        "specialties": ["Markham", "Residential", "Commercial", "Investors"],
    },
    {
        "title": "Susan Taylor Real Estate Group",
        "address": "72 Copper Creek Dr, Suite 101B, Markham, ON L6B 0P2",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 81,
        "website": "https://www.susantaylor.realtor/",
        "phoneNumber": "+1 905-472-4702",
        "category": "Real estate agent",
        "position": 7,
        "brokerage": "RE/MAX Prime Properties, Brokerage",
        "specialties": ["Markham", "Residential", "Sellers", "Buyers"],
    },
    {
        "title": "Nancy Jiang",
        "address": "8300 Woodbine Ave, Markham, ON L3R 9Y7",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 77,
        "website": "https://nancyjiangrealty.com/",
        "phoneNumber": "+1 647-677-3518",
        "category": "Real estate broker",
        "position": 8,
        "brokerage": "Bay Street Integrity Realty Inc., Brokerage",
        "specialties": ["Markham", "First-time Buyers", "Investors", "Residential"],
    },
    {
        "title": "Rita Chemilian Real Estate Team",
        "address": "161 Main St Unionville, Unionville, ON L3R 2G8",
        "locality": "Unionville",
        "rating": 5.0,
        "ratingCount": 73,
        "website": "https://www.ritachemilian.com/",
        "phoneNumber": "+1 647-360-5928",
        "category": "Real estate agent",
        "position": 9,
        "brokerage": "Royal LePage Your Community Realty, Brokerage",
        "specialties": ["Markham", "Residential", "Commercial", "Sellers"],
    },
    {
        "title": "Arthur Zhao",
        "address": "8300 Woodbine Ave, Suite 500, Markham, ON L3R 9Y7",
        "locality": "Markham",
        "rating": 5.0,
        "ratingCount": 50,
        "website": "https://www.google.com/maps/search/?api=1&query=Arthur+Zhao+Real+Estate+Broker+Markham+Ontario",
        "phoneNumber": "+1 416-888-6161",
        "category": "Real estate broker",
        "position": 10,
        "brokerage": "Bay Street Realty Group Inc., Brokerage",
        "specialties": ["Markham", "Luxury", "Investors", "First-time Buyers"],
    },
]


@dataclass(frozen=True)
class SourceCandidate:
    title: str
    address: str
    locality: str
    rating: float
    review_count: int
    website: str
    phone: str
    category: str
    best_position: int
    brokerage_hint: str = ""
    specialties_hint: tuple[str, ...] = ()


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def extract_fsa(address: str) -> str:
    match = re.search(r"\b([A-Z]\d[A-Z])\s*\d[A-Z]\d\b", address.upper())
    return match.group(1) if match else ""


def is_markham_address(address: str) -> bool:
    normalized = clean_text(address).upper()
    fsa = extract_fsa(normalized)
    locality_match = any(name in normalized for name in ("MARKHAM", "UNIONVILLE", "THORNHILL"))
    return fsa in MARKHAM_FSAS and locality_match


def looks_like_agent_or_team(title: str, category: str) -> bool:
    text = f"{title} {category}".lower()
    negative_only = (
        "real estate agency",
        "real estate company",
        "property management company",
    )
    positive = (
        "realtor",
        "real estate agent",
        "real estate broker",
        "broker",
        " team",
        " group",
        " associates",
    )
    if any(token in text for token in positive):
        return True
    if any(token in text for token in negative_only):
        return False
    words = re.findall(r"[A-Za-z]+", title)
    return 2 <= len(words) <= 7 and not any(
        suffix in text for suffix in ("realty inc", "realty ltd", "brokerage inc", "corporation")
    )


def normalize_source_item(item: dict[str, Any], fallback_position: int) -> SourceCandidate | None:
    title = clean_text(item.get("title") or item.get("name"))
    address = clean_text(item.get("address"))
    category = clean_text(item.get("category") or item.get("type"))
    if not title or not address or not is_markham_address(address):
        return None
    if not looks_like_agent_or_team(title, category):
        return None

    try:
        rating = clamp(float(item.get("rating") or 0), 0, 5)
    except (TypeError, ValueError):
        rating = 0.0
    try:
        review_count = max(0, int(item.get("ratingCount") or item.get("reviews") or 0))
    except (TypeError, ValueError):
        review_count = 0
    try:
        position = max(1, int(item.get("position") or fallback_position))
    except (TypeError, ValueError):
        position = fallback_position

    website = clean_text(item.get("website"))
    if website and not website.startswith("https://"):
        website = ""

    locality = clean_text(item.get("locality"))
    if not locality:
        if "UNIONVILLE" in address.upper():
            locality = "Unionville"
        elif "THORNHILL" in address.upper():
            locality = "Thornhill"
        else:
            locality = "Markham"

    specialties_raw = item.get("specialties") or []
    specialties = tuple(clean_text(value) for value in specialties_raw if clean_text(value))

    return SourceCandidate(
        title=title,
        address=address,
        locality=locality,
        rating=rating,
        review_count=review_count,
        website=website,
        phone=clean_text(item.get("phoneNumber") or item.get("phone")),
        category=category,
        best_position=position,
        brokerage_hint=clean_text(item.get("brokerage")),
        specialties_hint=specialties,
    )


def serper_maps_search(query: str) -> list[dict[str, Any]]:
    response = requests.post(
        SERPER_ENDPOINT,
        headers={
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        json={
            "q": query,
            "gl": "ca",
            "hl": "en",
            "location": "Markham, Ontario, Canada",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    places = payload.get("places") or payload.get("localResults") or []
    if not isinstance(places, list):
        return []
    return [item for item in places if isinstance(item, dict)]


def discover_live_candidates() -> list[SourceCandidate]:
    all_candidates: list[SourceCandidate] = []
    for query in DISCOVERY_QUERIES:
        items = serper_maps_search(query)
        for index, item in enumerate(items, start=1):
            candidate = normalize_source_item(item, index)
            if candidate:
                all_candidates.append(candidate)
        time.sleep(0.4)
    return deduplicate_candidates(all_candidates)


def candidate_key(candidate: SourceCandidate) -> str:
    host = urlparse(candidate.website).netloc.lower().removeprefix("www.")
    normalized_name = re.sub(r"[^a-z0-9]+", "", candidate.title.lower())
    if host and "google.com" not in host:
        return host + ":" + normalized_name[:30]
    return normalized_name


def deduplicate_candidates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    merged: dict[str, SourceCandidate] = {}
    for candidate in candidates:
        key = candidate_key(candidate)
        current = merged.get(key)
        if current is None:
            merged[key] = candidate
            continue

        merged[key] = SourceCandidate(
            title=current.title if len(current.title) <= len(candidate.title) else candidate.title,
            address=current.address or candidate.address,
            locality=current.locality or candidate.locality,
            rating=max(current.rating, candidate.rating),
            review_count=max(current.review_count, candidate.review_count),
            website=current.website or candidate.website,
            phone=current.phone or candidate.phone,
            category=current.category or candidate.category,
            best_position=min(current.best_position, candidate.best_position),
            brokerage_hint=current.brokerage_hint or candidate.brokerage_hint,
            specialties_hint=current.specialties_hint or candidate.specialties_hint,
        )
    return list(merged.values())


def robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = requests.get(
            robots_url,
            headers={"User-Agent": USER_AGENT},
            timeout=5,
        )
        if response.status_code >= 400:
            return True
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except requests.RequestException:
        return True


def fetch_website_text(url: str) -> tuple[str, list[str]]:
    if not url or "google.com/" in url:
        return "", []
    if not robots_allows(url):
        return "", []
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return "", []
        if len(response.content) > 2_000_000:
            return "", []

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        lines = [clean_text(value) for value in soup.stripped_strings]
        lines = [value for value in lines if value]
        return clean_text(" ".join(lines))[:120_000], lines[:4_000]
    except requests.RequestException:
        return "", []


def clean_brokerage_line(line: str) -> str:
    text = clean_text(line)
    text = re.sub(r"^(brokerage|office|presented by|powered by)\s*[:\-]\s*", "", text, flags=re.I)
    if len(text) > 120:
        text = text[:117].rstrip() + "..."
    return text


def infer_brokerage(candidate: SourceCandidate, page_lines: list[str]) -> str:
    if candidate.brokerage_hint:
        return candidate.brokerage_hint

    useful_terms = ("brokerage", "realty", "real estate")
    for line in page_lines:
        lower = line.lower()
        if len(line) > 180:
            continue
        if any(brand.lower() in lower for brand in BROKERAGE_BRANDS) and any(term in lower for term in useful_terms):
            return clean_brokerage_line(line)

    for line in page_lines:
        lower = line.lower()
        if len(line) <= 140 and "brokerage" in lower:
            return clean_brokerage_line(line)

    title_lower = candidate.title.lower()
    for brand in BROKERAGE_BRANDS:
        if brand.lower() in title_lower:
            return brand
    return "Brokerage not listed in source"


def infer_specialties(candidate: SourceCandidate, page_text: str) -> list[str]:
    if candidate.specialties_hint:
        values = list(dict.fromkeys(candidate.specialties_hint))
        return values[:4]

    haystack = f"{candidate.title} {candidate.category} {page_text}".lower()
    values = ["Markham"]
    for label, needles in SPECIALTY_KEYWORDS.items():
        if any(needle in haystack for needle in needles):
            values.append(label)
        if len(values) >= 4:
            break
    if len(values) == 1:
        values.extend(["Residential", "Buyers", "Sellers"])
    return values[:4]


def contact_link(candidate: SourceCandidate) -> str:
    if candidate.website.startswith("https://"):
        return candidate.website
    query = quote_plus(f"{candidate.title} {candidate.address}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def rank_score(candidate: SourceCandidate) -> float:
    # Bayesian prior reduces volatility for profiles with very few reviews.
    prior_mean = 4.6
    prior_weight = 25.0
    weighted_rating = (
        (candidate.review_count / (candidate.review_count + prior_weight)) * candidate.rating
        + (prior_weight / (candidate.review_count + prior_weight)) * prior_mean
    )
    review_quality_score = (weighted_rating / 5.0) * 60.0

    # Log scaling gives review depth credit without letting huge counts dominate.
    review_volume_score = min(
        math.log1p(candidate.review_count) / math.log1p(500), 1.0
    ) * 25.0

    # Position 1 gets the full 10 points; positions 20+ get zero.
    visibility_ratio = max(0.0, 1.0 - ((candidate.best_position - 1) / 19.0))
    visibility_score = visibility_ratio * 10.0

    profile_score = 5.0 if candidate.website.startswith("https://") else 2.0
    return round(review_quality_score + review_volume_score + visibility_score + profile_score, 1)


def build_realtor(candidate: SourceCandidate, use_website_enrichment: bool) -> dict[str, Any]:
    page_text = ""
    page_lines: list[str] = []
    if use_website_enrichment and candidate.website:
        page_text, page_lines = fetch_website_text(candidate.website)

    return {
        "name": candidate.title,
        "brokerage": infer_brokerage(candidate, page_lines),
        "rating": round(candidate.rating, 1),
        "review_count": candidate.review_count,
        "specialties": infer_specialties(candidate, page_text),
        "address": candidate.address,
        "locality": candidate.locality,
        "contact_link": contact_link(candidate),
        "phone": candidate.phone,
        "score": rank_score(candidate),
        "best_search_position": candidate.best_position,
        "rating_source": "Public business data via search-data provider",
    }


def payload_for(candidates: list[SourceCandidate], source_name: str, live: bool) -> dict[str, Any]:
    records = [build_realtor(candidate, use_website_enrichment=live) for candidate in candidates]
    records.sort(
        key=lambda row: (
            -float(row["score"]),
            -int(row["review_count"]),
            -float(row["rating"]),
            str(row["name"]).lower(),
        )
    )
    records = records[:TOP_LIMIT]
    for index, record in enumerate(records, start=1):
        record["rank"] = index

    return {
        "updated_at": date.today().isoformat(),
        "market": {
            "city": "Markham",
            "region": "Ontario",
            "country": "Canada",
        },
        "source": {
            "name": source_name,
            "mode": "live" if live else "development-seed",
            "note": (
                "Live candidates are discovered through a search-data API; selected agent websites may be read once for brokerage and specialty enrichment when robots.txt permits."
                if live
                else "Deterministic development seed for local builds. GitHub Actions is configured to require live data."
            ),
        },
        "methodology": {
            "summary": "Eligible profiles must show a Markham-area business address. Scores combine Bayesian-adjusted review quality (60%), log-scaled review volume (25%), observed local-search visibility (10%) and profile completeness (5%). No paid-placement factor is used.",
            "weights": {
                "bayesian_review_quality": 60,
                "review_volume": 25,
                "local_search_visibility": 10,
                "profile_completeness": 5,
            },
            "eligibility": "Public business address must be in an accepted Markham-area postal prefix and the result must identify an agent, broker or real estate team rather than a generic brokerage office.",
        },
        "realtors": records,
    }


def comparable_payload(payload: dict[str, Any]) -> dict[str, Any]:
    copy = dict(payload)
    copy.pop("updated_at", None)
    return copy


def load_existing() -> dict[str, Any] | None:
    if not OUTPUT_FILE.exists():
        return None
    try:
        return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_if_changed(payload: dict[str, Any]) -> bool:
    existing = load_existing()
    if existing is not None and comparable_payload(existing) == comparable_payload(payload):
        print("No material directory changes detected; realtors.json left unchanged.")
        return False

    temporary = OUTPUT_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(OUTPUT_FILE)
    print(f"Updated {OUTPUT_FILE.name} with {len(payload['realtors'])} ranked profiles.")
    return True


def main() -> int:
    if SERPER_API_KEY:
        print("Using live Serper Maps data.")
        try:
            candidates = discover_live_candidates()
        except requests.RequestException as exc:
            print(f"Live data request failed: {exc}", file=sys.stderr)
            return 2
        if len(candidates) < MINIMUM_LIVE_RESULTS:
            print(
                f"Safety stop: only {len(candidates)} eligible live profiles were found; "
                f"at least {MINIMUM_LIVE_RESULTS} are required.",
                file=sys.stderr,
            )
            return 3
        payload = payload_for(candidates, "Serper Maps API", live=True)
    else:
        if REQUIRE_LIVE_DATA:
            print(
                "SERPER_API_KEY is missing. GitHub Actions requires live data and will not publish the development seed.",
                file=sys.stderr,
            )
            return 4
        print("SERPER_API_KEY not set; using deterministic development seed data.")
        candidates = [
            candidate
            for index, item in enumerate(MOCK_SOURCE_DATA, start=1)
            if (candidate := normalize_source_item(item, index)) is not None
        ]
        payload = payload_for(candidates, "Development seed snapshot", live=False)

    if not payload["realtors"]:
        print("No eligible Markham realtor profiles were produced.", file=sys.stderr)
        return 5

    write_if_changed(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
