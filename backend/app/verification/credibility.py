"""Deterministic source credibility: (level, reason). The LLM never decides credibility."""
from app.utils.text import company_core

HIGH = {
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "nytimes.com", "cnbc.com", "techcrunch.com", "theverge.com",
    "axios.com", "fortune.com", "forbes.com", "businessinsider.com", "economist.com", "economictimes.indiatimes.com",
    "livemint.com", "business-standard.com", "thehindubusinessline.com", "moneycontrol.com", "inc42.com",
    "yourstory.com", "venturebeat.com", "sec.gov", "wired.com", "bbc.co.uk", "bbc.com", "theinformation.com",
    "fastcompany.com", "hbr.org", "irishtimes.com", "paymentsdive.com", "pymnts.com", "forrester.com",
    "theguardian.com", "apnews.com",
}
PRESS_WIRES = {"prnewswire.com", "businesswire.com", "globenewswire.com", "accesswire.com"}
JOB_BOARDS = {
    "greenhouse.io", "lever.co", "myworkdayjobs.com", "ashbyhq.com", "indeed.com", "glassdoor.com", "wellfound.com",
    "naukri.com", "linkedin.com", "smartrecruiters.com", "builtin.com", "builtinchicago.org", "jobzmall.com",
}
MEDIUM = {
    "crunchbase.com", "wikipedia.org", "techradar.com", "zdnet.com", "siliconangle.com", "youtube.com",
    "spotify.com", "podcasts.apple.com", "substack.com", "a16z.com", "finovate.com", "tradingview.com",
}
LOW = {
    "medium.com", "quora.com", "reddit.com", "zoominfo.com", "rocketreach.co", "apollo.io", "signalhire.com",
    "theorg.com", "craft.co", "owler.com", "instagram.com", "facebook.com", "x.com", "twitter.com", "tiktok.com",
    "tavily.com",
}


def registrable(domain: str) -> str:
    """news.example.co.uk -> example.co.uk ; boards.greenhouse.io -> greenhouse.io"""
    parts = domain.lower().removeprefix("www.").split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "ac", "gov"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_official(domain: str, company: str) -> bool:
    slug = company_core(company).replace(" ", "").replace("-", "")
    label = registrable(domain).split(".")[0].replace("-", "")
    return len(slug) >= 3 and (slug == label or (len(slug) >= 5 and label.startswith(slug)))


def _in(domain: str, reg: str, names: set[str]) -> bool:
    """Match either the full host (economictimes.indiatimes.com) or the registrable domain (techcrunch.com)."""
    host = domain.lower().removeprefix("www.")
    return host in names or reg in names


def assess(domain: str, claim_type: str, company: str) -> tuple[str, str]:
    reg = registrable(domain)
    if is_official(domain, company):
        return "high", "Official company source"
    if _in(domain, reg, HIGH) or reg.endswith((".gov", ".edu", ".gov.in")):
        return "high", "Established news / official publication"
    if _in(domain, reg, PRESS_WIRES):
        return "medium", "Press release (self-published announcement)"
    if _in(domain, reg, JOB_BOARDS):
        if claim_type == "hiring":
            return "medium", "Job board listing"
        return "low", "Job board used for a non-hiring claim"
    if _in(domain, reg, MEDIUM):
        return "medium", "Secondary reference source"
    if _in(domain, reg, LOW):
        return "low", "User-generated, social or data-broker source"
    return "low", "Unrecognised publisher — needs corroboration"
