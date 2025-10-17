# Example Rules

This directory contains sample detection rules from various platforms to demonstrate the conversion process.

## Directory Structure

```
examples/
├── okta/                    # Okta identity platform rules
├── crowdstrike/             # CrowdStrike EDR rules
├── windows/                 # Windows endpoint rules
└── sigma/                   # Sigma universal rules
```

## How to Use These Examples

### Test the Conversion Tool

You can use these examples to test the conversion tool before using your own rules:

```bash
# From the project root directory
python convert_rules.py \
  --oid "your-org-id" \
  --api-key "your-api-key" \
  --platform "okta" \
  --rules-dir "./examples/okta" \
  --skip-confirmation
```

### Learn the Input Format

These examples show the flexibility of the conversion tool. It accepts:

- **Plain text descriptions** (`okta/suspicious_login_impossible_travel.txt`)
- **YAML structured rules** (`okta/brute_force_attack.yaml`)
- **JSON formatted rules** (`crowdstrike/malware_execution_detected.json`)
- **Sigma rules** (`sigma/credential_dumping_lsass.yml`)
- **Custom formats** (any text-based rule description)

The AI-powered conversion tools can interpret various formats and convert them to LimaCharlie D&R rules.

## Example Descriptions

### Okta Examples

**suspicious_login_impossible_travel.txt**
- Detects impossible travel scenarios (logins from distant locations in short time)
- Plain text description format
- High severity credential access detection

**brute_force_attack.yaml**
- Detects multiple failed login attempts indicating brute force attacks
- YAML format with structured detection logic
- Medium severity with IP blocking response

### CrowdStrike Examples

**malware_execution_detected.json**
- Detects malware execution events from CrowdStrike Falcon
- JSON format rule
- Critical severity with optional host isolation

### Windows Examples

**privilege_escalation_attempt.yml**
- Detects privilege escalation via token manipulation
- YAML format with detailed conditions and exclusions
- High severity endpoint detection

### Sigma Examples

**credential_dumping_lsass.yml**
- Universal Sigma rule format for credential dumping
- Detects LSASS memory access for credential theft
- Includes false positive filters

## Platform Setup Requirements

Before converting these examples, ensure you have the corresponding platform configured in LimaCharlie:

| Platform | Example Rules | LimaCharlie Setup Required |
|----------|---------------|----------------------------|
| Okta | okta/* | Okta adapter configured and ingesting auth logs |
| CrowdStrike | crowdstrike/* | CrowdStrike Falcon adapter configured |
| Windows | windows/* | Windows sensors deployed OR Windows Event Log adapter |
| Sigma (Windows) | sigma/* | Windows platform (sensors or event logs) |

## Expected Output Format

All examples will be converted to LimaCharlie D&R format:

```yaml
detect:
  event: [event_type]
  op: [operator]
  rules:
    - [conditions]

respond:
  - action: report
    name: [alert_name]
  - action: [additional_actions]
```

## Converting Your Own Rules

Once you've tested with these examples and understand the process:

1. Create a new directory for your rules
2. Copy your existing rules into that directory
3. Run the conversion script pointing to your directory
4. Review the converted rules in the output directory

## Testing Converted Rules

After conversion, test the rules using LimaCharlie's Replay service:

```bash
# Validate rule syntax
limacharlie replay --validate --rule-content output/rule_name.yaml

# Test against historical data
limacharlie replay \
  --rule-content output/rule_name.yaml \
  --entire-org \
  --last-seconds 86400
```

## Questions?

See the main [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) for detailed instructions or [README.md](../README.md) for troubleshooting help.
