"""
CDP Documentation scrapper
Scraps AEP, Segment, and mParticle public documentation for the CDP RAG Knowledge Assistant. 

Design Decisions:
- Use httpx over requests for async support and better performance.
- Respect robots.txt and rate limits to avoid being blocked or banned.
- Preserves metadata(source, section, date) for staleness detection
- Stores raw HTML + Extracted text separately fo debugging
"""

import httpx
import time
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
from bs4 import BeautifulSoup



#logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Data model

class ScrapDocument:
    """
    Represents a single scraped documention page. 
    Metadata is preserved here for downstream chunking
    and staleness detection. 
    """
    doc_id: str #SHA256 hash of the URL - stable unique identifier for the document
    url : str
    title: str
    content: str #cleaned text content
    source: str   # e.g. "aep" ,"segment" ,"mparticle"
    section: str  #Top-level doc section e.g. "indentity","segmentation"
    scraped_at: str #ISO format timestamp
    content_length: int
    last_modified: Optional[str] = None #From HTTP headers if available


#Source configuration
# Add more URLs as knowledge base expands
#Keep URLs focussed - quality over quantity
SOURCES = {
    "aep":[
        "https://experienceleague.adobe.com/docs/experience-platform/identity/home.html",
        "https://experienceleague.adobe.com/docs/experience-platform/segmentation/home.html",
        "https://experienceleague.adobe.com/docs/experience-platform/profile/home.html",
        "https://experienceleague.adobe.com/docs/experience-platform/xdm/home.html",
        "https://experienceleague.adobe.com/docs/experience-platform/data-governance/home.html",
    ],
    "segment": [
        "https://segment.com/docs/getting-started/",
        "https://segment.com/docs/connections/",
        "https://segment.com/docs/personas/",
    ],
    "mparticle": [
        "https://docs.mparticle.com/guides/getting-started/",
        "https://docs.mparticle.com/guides/platform-guide/",
    ]
}


#Scrapper logic
class CDPScrapper:
    """
    Scrapes CDP documentation pages.

    Design Pricinciples:
    - Polite scrapping: 2 second delay between requests. 
    - Idempotent: skips already-scraped URLs using doc_id check.
    - Fail-safe: logs errors and continues rather than crashing.
    - Debug friendly
    """

    def __init__(
            self,
            output_dir: str = "data/raw",
            delay_seconds: float = 2.0
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay_seconds = delay_seconds
        self.headers = {
            "User-Agent":
            (
                "CDPKnowledgeAssistant/1.0"
                "(Portofolio project: github.com/arkanild/cdp-rag-assistant)"
            )
        }

    def _make_doc_id(self, url:str)-> str:
        """stable unique ID from URL - same URL always produces same ID"""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def _already_scraped(self, doc_id:str) -> bool:
        """check output directory skip if already exists"""
        return (self.output_dir / f"{doc_id}.json").exists()
    
    def _extract_content(self, url:str, html:str)-> tuple[str,str]:
        """
        Extract clean text and title from html.
        removes: navigation, headers, footers, scripts, styles. 
        preserves: headings, paragraphs, code blocks, lists.
        Returns: (title, clean_text)
        """
        soup = BeautifulSoup(html, "html.parser")

        #remove noise elements
        for element in soup(["nav","header", "footer", "script", "style", "aside", "advertisement"]):
            element.decompose()
        
        #extract title
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)

        
        #Extract main content - try common contents containers first
        main_content = (
            soup.find("main") or 
            soup.find("article") or
            soup.find(class_ = ["content", "main-content","doc-content"]) or
            soup.find("body")
        )

        if not main_content:
            return title, ""
        
        #Get clean text preserving some structure
        lines = []
        for element in main_content.final_all(
            ["h1", "h2", "h3", "h4", "p", "li", "code", "pre"]
        ):
            text = element.get_text(strip=True)
            if text and len(text) > 20: #skip nouse fragments 
                #Add heading markers for chunker to use later
                if element.name in ["h1","h2","h3","h4"]:
                    lines.append(f"\n## {text}\n")
                elif element.name in ["code","pre"]:
                    lines.append(f"```\n{text}\n```")
                else: 
                    lines.append(text)
        
        return title, "\n".join(lines)
    
    def _infer_section(self, url:str) -> str:
        """
        Infer document section from URL path.
        Used for metadata and filtering downstream.
        """
        url_lower = url.lower()
        section_keywords = {
                        "identity": ["identity", "id-graph", "id_graph"],
            "segmentation": ["segment", "audience", "persona"],
            "profile": ["profile", "customer-profile"],
            "schema": ["xdm", "schema", "data-model"],
            "governance": ["governance", "consent", "privacy", "dule"],
            "journey": ["journey", "activation", "orchestration"],
            "ingestion": ["ingestion", "source", "connector", "pipeline"]
        }
        for section, keywords in section_keywords.items():
            if any(kw in url_lower for kw in keywords):
                return section
            return "general"
        
    
    def scrape_url(
            self, 
            url: str, 
            source: str
    ) -> Optional[ScrapDocument]:
        """
        scrap a single URl
        returns ScrapDocument or None if failed/skipped.
        """
        doc_id = self._make_doc_id(url)

        #Skip if already scraped - idempotency
        if self._already_scraped(doc_id):
            logger.info(f"Skipping already scraped: {url}")
            return None
        
        try:
            logger.info(f"scrapping: {url}")
            response = httpx.get(
                url,
                headers = self.headers,
                timeout = 30,
                follow_redirects = True
            )
            response.raise_for_status()

            #Extract last modified from headers if available
            last_modified = response.headers.get("last-modified")
            