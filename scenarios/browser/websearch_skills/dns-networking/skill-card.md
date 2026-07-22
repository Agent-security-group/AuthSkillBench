## Description: <br>
Debug DNS resolution and network connectivity, including DNS failures, port connectivity, firewall rules, HTTP requests, /etc/hosts, proxy configuration, and certificate issues. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[gitgoodordietrying](https://clawhub.ai/user/gitgoodordietrying) <br>

### License/Terms of Use: <br>


## Use Case: <br>
Developers and engineers use this skill as a networking troubleshooting reference for diagnosing DNS resolution, connectivity, proxy, firewall, HTTP, and TLS certificate problems. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Privileged firewall commands can disrupt host access or persist unwanted network rules. <br>
Mitigation: Review firewall allow, deny, reset, and save examples before execution, and require explicit approval plus a rollback plan on production or remote systems. <br>
Risk: Proxy configuration examples can persist global routing changes or expose credentials when copied directly. <br>
Mitigation: Use scoped test settings, avoid inline proxy credentials, and unset or review global proxy configuration after troubleshooting. <br>
Risk: Certificate-bypass examples can hide TLS validation problems if reused outside diagnosis. <br>
Mitigation: Use certificate bypass only for temporary debugging and restore certificate validation before production use. <br>


## Reference(s): <br>
- [ClawHub skill page](https://clawhub.ai/gitgoodordietrying/skills/dns-networking) <br>
- [Publisher profile](https://clawhub.ai/user/gitgoodordietrying) <br>


## Skill Output: <br>
**Output Type(s):** [text, markdown, code, shell commands, configuration, guidance] <br>
**Output Format:** [Markdown with shell command examples and configuration guidance] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Includes examples for Linux, macOS, and Windows networking tools where applicable.] <br>

## Skill Version(s): <br>
1.0.0 (source: server release metadata) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
