## Description: <br>
Automate web browser interactions using natural language via CLI commands. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[peytoncasper](https://clawhub.ai/user/peytoncasper) <br>

### License/Terms of Use: <br>


## Use Case: <br>
Developers and agents use this skill to navigate websites, perform natural-language browser actions, extract structured data, capture screenshots, and automate web workflows through a browser CLI. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: The skill can run broad browser actions that may submit forms, change accounts, or interact with the wrong page element. <br>
Mitigation: Review screenshots and observations after each step, use specific action descriptions, and manually confirm any form submission, account change, download, or authenticated workflow. <br>
Risk: Browser sessions, screenshots, and downloads may retain sensitive data. <br>
Mitigation: Use a dedicated browser profile and test accounts, avoid sensitive sites unless necessary, and clear stored profile data and generated files after use. <br>
Risk: Remote browser mode is selected automatically when Browserbase keys are present. <br>
Mitigation: Explicitly check the configured environment before use and choose local or remote mode intentionally for the sensitivity of the task. <br>
Risk: Setup exposes a globally linked browser CLI after installing dependencies. <br>
Mitigation: Install only after inspecting or trusting the CLI package and run it in a controlled environment. <br>


## Reference(s): <br>
- [Browser Automation release page](https://clawhub.ai/peytoncasper/skills/browser-automation) <br>
- [Browser Automation examples](artifact/EXAMPLES.md) <br>
- [Browser Automation CLI reference](artifact/REFERENCE.md) <br>


## Skill Output: <br>
**Output Type(s):** [Shell commands, Configuration instructions, Guidance, Files] <br>
**Output Format:** [Markdown guidance with bash commands and JSON command results] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Commands may save PNG screenshots and downloaded files to local agent directories.] <br>

## Skill Version(s): <br>
1.0.1 (source: server release evidence) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
