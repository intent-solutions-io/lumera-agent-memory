"""Memory Card generation using deterministic NLP heuristics.

WOW Factor: Extract title, summary, decisions, todos, entities, keywords, quotes
from session data without any network calls or ML models.
"""

import re
from typing import Dict, Any, List


def extract_sentences(text: str) -> List[str]:
    """Split text into sentences (simple heuristic)."""
    # Simple sentence splitter
    sentences = re.split(r'[.!?]+\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def extract_keywords(text: str, max_keywords: int = 20) -> List[str]:
    """Extract keywords using simple frequency-based heuristic."""
    # Remove common words (stopwords)
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'was', 'are', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'could', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'on', 'at', 'for',
        'with', 'from', 'by', 'as', 'it', 'this', 'that', 'these', 'those', 'i', 'you',
        'he', 'she', 'they', 'we', 'what', 'when', 'where', 'why', 'how', 'which'
    }

    # Tokenize and count
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    word_freq = {}
    for word in words:
        if word not in stopwords and len(word) > 2:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency and return top N
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_keywords]]


def extract_entities(text: str) -> List[str]:
    """Extract entities using simple regex heuristics (no ML)."""
    entities = []

    # Organizations (capitalized multi-word phrases)
    org_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b')
    orgs = org_pattern.findall(text)
    entities.extend(orgs[:5])  # Max 5 org names

    # Domains/products (alphanumeric with hyphens)
    domain_pattern = re.compile(r'\b([A-Z][a-zA-Z0-9-]+)\b')
    domains = domain_pattern.findall(text)
    entities.extend([d for d in domains if len(d) > 3][:5])

    # Deduplicate and limit
    seen = set()
    unique_entities = []
    for entity in entities:
        if entity not in seen and len(entity) > 2:
            seen.add(entity)
            unique_entities.append(entity)
    return unique_entities[:15]


def extract_decisions(text: str) -> List[str]:
    """Extract decision-like statements."""
    decision_patterns = [
        r"(?:decided|chose|selected|picked)\s+(?:to\s+)?([^.!?]{10,100})",
        r"(?:will|going to)\s+([^.!?]{10,100})",
        r"(?:approved|rejected|accepted)\s+([^.!?]{10,100})",
    ]

    decisions = []
    for pattern in decision_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        decisions.extend(matches)

    # Clean and limit
    decisions = [d.strip() for d in decisions if len(d.strip()) > 10]
    return decisions[:5]


def extract_todos(text: str) -> List[str]:
    """Extract TODO/action items."""
    todo_patterns = [
        r"(?:TODO|FIXME|ACTION):\s*([^.\n]{5,100})",
        r"(?:need to|must|should)\s+([^.!?]{10,100})",
        r"(?:next steps?|action items?):\s*([^.!?]{10,100})",
    ]

    todos = []
    for pattern in todo_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        todos.extend(matches)

    # Clean and limit
    todos = [t.strip() for t in todos if len(t.strip()) > 5]
    return todos[:7]


def extract_notable_quotes(text: str) -> List[str]:
    """Extract quoted text (literal quotes)."""
    # Find text in quotes
    quote_pattern = re.compile(r'["\'](.*?)["\']')
    quotes = quote_pattern.findall(text)

    # Filter: 10-160 chars
    notable = [q for q in quotes if 10 <= len(q) <= 160]
    return notable[:5]


def generate_title(session: Dict[str, Any]) -> str:
    """Generate a title for the session."""
    # Prefer explicit summary field
    if "summary" in session and session["summary"]:
        summary = session["summary"]
        # Take first sentence or first 60 chars
        first_sentence = re.split(r'[.!?]', summary)[0].strip()
        if len(first_sentence) < 60:
            return first_sentence
        return summary[:60].rsplit(' ', 1)[0] + "..."

    # Fallback: session_id + tool_name
    session_id = session.get("session_id", "unknown")
    tool_name = session.get("tool_name", "")
    if tool_name:
        return f"{tool_name}: {session_id}"
    return f"Session {session_id}"


def generate_summary_bullets(session: Dict[str, Any]) -> List[str]:
    """Generate 3-7 summary bullet points."""
    # Extract key information
    bullets = []

    # Session metadata
    tool = session.get("tool_name")
    success = session.get("success")
    if tool:
        status = "succeeded" if success else "failed"
        bullets.append(f"Tool: {tool} ({status})")

    # Summary field
    summary = session.get("summary", "")
    if summary:
        sentences = extract_sentences(summary)
        bullets.extend(sentences[:3])

    # Tags
    tags = session.get("tags", [])
    if tags:
        bullets.append(f"Tags: {', '.join(tags[:5])}")

    # Ensure 3-7 bullets
    if len(bullets) < 3:
        bullets.append(f"Session ID: {session.get('session_id', 'unknown')}")
        bullets.append(f"Timestamp: {session.get('timestamp', 'unknown')}")

    return bullets[:7]


def generate_memory_card(session: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a Memory Card from session data.

    Uses deterministic NLP heuristics (no network, no ML models).

    Args:
        session: Session data dict

    Returns:
        Memory card dict with title, summary_bullets, decisions, todos, entities, keywords, notable_quotes
    """
    # Concatenate all text fields for analysis
    text_parts = []
    for key in ["summary", "tool_name", "error_message", "output"]:
        if key in session and session[key]:
            text_parts.append(str(session[key]))
    full_text = " ".join(text_parts)

    return {
        "title": generate_title(session),
        "summary_bullets": generate_summary_bullets(session),
        "decisions": extract_decisions(full_text),
        "todos": extract_todos(full_text),
        "entities": extract_entities(full_text),
        "keywords": extract_keywords(full_text),
        "notable_quotes": extract_notable_quotes(full_text),
    }
