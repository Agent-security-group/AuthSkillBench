# Synthetic Email + Browser Scenario

This scenario lets one agent task use both email and browser tools. It is meant
to test whether a trusted skill invocation stays within the user's concrete
authorization when web content, email context, recipients, URLs, and data
movement interact.

## Layout

```text
scenarios/synthetic/email_browser/
  app/
    api.py
    runtime.py
    benchmark.py
    candidate_selection.py
    agent_runner.py
  data/
    state.json
    toolkits/email_browser.json
    skills/*.json
    tasks/<family>/*.json
    threats/<type>/*.json
    contrast_groups/*.json
  outputs/
  scripts/
```

## Tool Names

Email component tools are prefixed with `email.`, for example:

```text
email.email.read_message
email.gmail.users.messages.send
```

Browser compatibility tools are prefixed with `browser.`, for example:

```text
browser.check_url_safety
browser.read_cached_page
browser.fetch_web_page
```

Function-call-safe aliases replace dots with double underscores.

## Case Count

The initial data contains 9 cases:

- 3 benign
- 3 ambiguous
- 3 adversarial_untrusted

Threat profiles use `scenario_overlays` so one synthetic threat can apply state
changes to both Email and Browser.

