"""Bounded official-source discovery. Failed reads remain explicitly incomplete."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from research.artifacts import digest, save_json

ATOM = {'a': 'http://www.w3.org/2005/Atom'}


def parse_feed(xml):
    rows = {}
    for entry in ET.fromstring(xml).findall('a:entry', ATOM):
        def text(key):
            return ' '.join((entry.findtext('a:' + key, '', ATOM)).split())
        identifier = re.sub(r'v\d+$', '', text('id').split('/abs/')[-1])
        if not re.fullmatch(r'(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})', identifier):
            raise ValueError('arXiv returned an error or unsupported identifier')
        rows[identifier] = {'id': identifier, 'version_url': text('id').replace('http:', 'https:'),
            'url': 'https://arxiv.org/abs/' + identifier, 'title': text('title'),
            'abstract': text('summary'), 'published': text('published'),
            'authors': [a.findtext('a:name', '', ATOM) for a in entry.findall('a:author', ATOM)]}
    return list(rows.values())


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(); self.depth = 0; self.hidden = 0; self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'article': self.depth += 1
        if tag in ('script', 'style'): self.hidden += 1
        if self.depth and tag in ('p', 'h1', 'h2', 'h3', 'li'): self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag == 'article': self.depth = max(0, self.depth - 1)
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if self.depth and not self.hidden: self.parts.append(data)


def make_chunks(identifier, text):
    return [{'id': f'{identifier}:c{i // 1200}', 'text': text[i:i + 1200]}
            for i in range(0, len(text), 1200)]


class ArxivClient:
    def __init__(self, directory, timeout=25):
        self.directory = directory; self.timeout = timeout; self.last_request = 0
        self.events = []

    def fetch(self, url):
        if urlsplit(url).hostname not in ('arxiv.org', 'export.arxiv.org'):
            raise ValueError('Only official arXiv endpoints are supported')
        time.sleep(max(0, 3.1 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        request = Request(url, headers={'User-Agent': 'JiuwenSwarmPaperAgent/0.1 (bounded research client)'})
        with urlopen(request, timeout=self.timeout) as response:
            if urlsplit(response.url).hostname not in ('arxiv.org', 'export.arxiv.org'):
                raise ValueError('Unexpected redirect')
            data = response.read(6_000_001)
            if len(data) > 6_000_000: raise ValueError('Source exceeds retrieval size ceiling')
        return data.decode('utf-8')

    def search(self, query, limit=6):
        if not isinstance(query, str) or not 1 <= len(query) <= 500 or not 1 <= limit <= 12:
            raise ValueError('Bounded query and result count required')
        url = 'https://export.arxiv.org/api/query?' + urlencode({
            'search_query': query, 'start': 0, 'max_results': limit, 'sortBy': 'relevance'})
        raw = self.fetch(url)
        rows = parse_feed(raw)
        event = {'query': query, 'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                 'response_sha256': digest(raw), 'results': rows}
        self.events.append(event)
        save_json(self.directory / f'search_{len(self.events):02d}.json', event)
        return rows

    def read(self, paper, max_chars=8000):
        row = dict(paper)
        url = paper['version_url'].replace('/abs/', '/html/')
        try:
            raw = self.fetch(url)
            parser = ArticleText(); parser.feed(raw)
            text = ' '.join(' '.join(parser.parts).split())
            if len(text) < 1000: raise ValueError('No usable article body')
            row.update(reading_scope='full_text_excerpt', read_url=url,
                       source_sha256=digest(raw), available_characters=len(text), read_error=None)
        except (OSError, ValueError) as error:
            text = paper['abstract']
            row.update(reading_scope='abstract_only', read_url=paper['url'],
                       source_sha256=digest(text), available_characters=len(text),
                       read_error=type(error).__name__)
        row['excerpt_char_limit'] = max_chars
        row['chunks'] = make_chunks(paper['id'], text[:max_chars])
        return row
