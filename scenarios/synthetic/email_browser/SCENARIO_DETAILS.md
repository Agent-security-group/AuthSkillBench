# Synthetic Email + Browser Details

## Integration Method

The synthetic runtime is a facade:

```text
EmailBrowserSyntheticRuntime
  -> EmailScenarioAPI
  -> BrowserScenario runtime compatibility adapter
```

It does not change the original Email or Browser scenario directories. The
Browser wrapper intentionally exposes only runtime methods that are currently
callable from the local browser implementation.

## Threat Shape

```json
{
  "threat_profile_id": "example",
  "threat_type": "adversarial_untrusted",
  "scenario_overlays": {
    "email": {
      "state_overlay": {"ops": []},
      "observation_refs": []
    },
    "browser": {
      "state_overlay": {"ops": []},
      "observation_refs": []
    }
  }
}
```

## Candidate Selection

Candidate invocation means the consequential skill/tool call that may be
unreasonable under the task authorization. The trajectory also records a
`candidate_chain` of high-impact cross-scenario calls that led to it.

