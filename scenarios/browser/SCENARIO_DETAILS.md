# Browser Scenario - AuthSkillBench

## Overview

The Browser scenario tests authorization decisions for web page fetching skills in various threat contexts. It follows the same architecture as the Email scenario, with separated data files, state management, and runtime layers.

## Directory Structure

```
scenarios/browser/
©À©¤©¤ __init__.py
©À©¤©¤ SCENARIO_DETAILS.md
©À©¤©¤ app/
©¦   ©À©¤©¤ __init__.py
©¦   ©À©¤©¤ api.py          # Agent-facing API wrapper
©¦   ©À©¤©¤ benchmark.py    # Benchmark sample generation
©¦   ©À©¤©¤ candidate_selection.py  # Candidate invocation selection
©¦   ©¸©¤©¤ runtime.py      # Core scenario implementation
©À©¤©¤ data/
©¦   ©À©¤©¤ state.json      # Base state definition
©¦   ©À©¤©¤ skills/
©¦   ©¦   ©¸©¤©¤ fetch_web_page.json
©¦   ©À©¤©¤ tasks/
©¦   ©¦   ©¸©¤©¤ fetch_web_page/
©¦   ©¦       ©À©¤©¤ fetch_products_release.json
©¦   ©¦       ©À©¤©¤ fetch_tech_docs.json
©¦   ©¦       ©À©¤©¤ fetch_internal_docs.json
©¦   ©¦       ©¸©¤©¤ fetch_with_cache_available.json
©¦   ©À©¤©¤ threats/
©¦   ©¦   ©À©¤©¤ benign/
©¦   ©¦   ©¦   ©À©¤©¤ benign_product_page.json
©¦   ©¦   ©¦   ©¸©¤©¤ benign_tech_docs.json
©¦   ©¦   ©À©¤©¤ adversarial_untrusted/
©¦   ©¦   ©¦   ©À©¤©¤ adversarial_phishing_redirect.json
©¦   ©¦   ©¦   ©¸©¤©¤ adversarial_internal_exfiltration.json
©¦   ©¦   ©¸©¤©¤ ambiguous/
©¦   ©¦       ©À©¤©¤ ambiguous_url_unknown.json
©¦   ©¦       ©¸©¤©¤ ambiguous_internal_permissions.json
©¦   ©À©¤©¤ contrast_groups/
©¦   ©¦   ©À©¤©¤ fetch_web_page_normal_authorized.json
©¦   ©¦   ©À©¤©¤ fetch_web_page_target_deviation.json
©¦   ©¦   ©À©¤©¤ fetch_web_page_ambiguous_authorization.json
©¦   ©¦   ©¸©¤©¤ fetch_web_page_alternative_available.json
©¦   ©¸©¤©¤ toolkits/
©¦       ©¸©¤©¤ browser_scenario.json
©¸©¤©¤ outputs/
    ©¸©¤©¤ benchmark_browser.json  # Generated output
```

## Task Types

| Task Type | Description |
|-----------|-------------|
| normal_authorized | Normal authorized task with clear permissions |
| target_deviation | Task with potential target deviation threats |
| ambiguous_authorization | Task with ambiguous authorization requirements |
| alternative_available | Task where a lower-privilege alternative exists |

## Environment Types

| Env Type | Description |
|----------|-------------|
| benign | Trusted environment with no threats |
| adversarial_untrusted | Malicious environment with deceptive content |
| ambiguous | Environment with unclear trust status |

## Risk Types

| Risk Type | Description |
|-----------|-------------|
| confidentiality_breach | Accessing internal OA, backend systems, or sensitive documents |
| wrong_target | Accessing incorrect domains, phishing pages, or malicious sites |
| scope_expansion | Bulk scraping, downloading sensitive attachments, or cookie leakage |

## Skills Under Test

- **fetch_web_page**: Fetch web pages and extract content
  - Alternatives: `read_cached_page` (low-privilege)

## Tools

| Tool | Description |
|------|-------------|
| fetch_web_page | Fetch a web page by URL |
| read_cached_page | Read cached page without network request |
| list_cached_pages | List all cached pages |
| check_url_safety | Check URL safety against domain policies |
| list_downloaded_files | List downloaded files |
| get_page_metadata | Get metadata about internal pages |
| clear_cookies | Clear internal session cookies |

## Running the Benchmark

```bash
cd scenarios/browser/app
python benchmark.py
```

## Using the API

```python
from scenarios.browser import BrowserScenarioAPI

api = BrowserScenarioAPI()
print(api.manifest())
result = api.invoke("fetch_web_page", {"target_url": "https://www.example.com"})
```

## Schema Versions

- State: `authskillbench.browser_scenario.state.v1`
- API: `authskillbench.browser_scenario.api.v1`
