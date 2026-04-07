# soyo1

MaixCAM laser and A4 paper detection project.

## Documentation Scraper (Firecrawl)

A utility script scrapes MaixCAM/K230 API documentation using [Firecrawl](https://firecrawl.dev) and saves it as markdown for offline reference.

### Setup

```bash
pip install -r requirements.txt
```

### Usage

```bash
export FIRECRAWL_API_KEY=your_api_key_here
python scrape_maix_docs.py
```

Scraped documents are saved to the `docs/` directory.
