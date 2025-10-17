# LimaCharlie Rule Migration Guide

Convert your security detection rules from other platforms (Splunk, Elastic, Sigma, CrowdStrike, Okta, etc.) into LimaCharlie Detection & Response (D&R) rules.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step 1: Set Up Your LimaCharlie Account](#step-1-set-up-your-limacharlie-account)
- [Step 2: Configure Data Ingestion](#step-2-configure-data-ingestion)
- [Step 3: Prepare Your Rules](#step-3-prepare-your-rules)
- [Step 4: Run the Conversion Script](#step-4-run-the-conversion-script)
- [Step 5: Review and Test Converted Rules](#step-5-review-and-test-converted-rules)
- [Step 6: Deploy Rules to Production](#step-6-deploy-rules-to-production)
- [Troubleshooting](#troubleshooting)
- [Appendix](#appendix)

---

## Overview

This guide walks you through migrating detection rules from other security platforms into LimaCharlie's Detection & Response (D&R) framework. The migration uses AI-powered tools from the LimaCharlie MCP (Model Context Protocol) server to automatically convert your existing rules into LimaCharlie's YAML-based D&R format.

### What You'll Accomplish

1. Set up your LimaCharlie environment
2. Configure data ingestion from your source platform
3. Convert existing rules to LimaCharlie D&R format
4. Test and validate the converted rules
5. Deploy rules to your production environment

### Migration Time Estimate

- **Small rule set (1-10 rules)**: 30-60 minutes
- **Medium rule set (10-50 rules)**: 1-2 hours
- **Large rule set (50+ rules)**: 2-4 hours

---

## Prerequisites

Before starting the migration, ensure you have:

### Required

- **LimaCharlie Account**: Sign up at [https://app.limacharlie.io](https://app.limacharlie.io)
- **API Key**: Generated from your LimaCharlie organization (see instructions below)
- **Python 3.8+**: For running the conversion script
- **Source Rules**: Your existing detection rules in their original format
- **Platform Knowledge**: Understanding of which platform your rules target (e.g., `okta`, `crowdstrike`, `windows`, `linux`)

### Recommended

- **LimaCharlie CLI**: For advanced testing and deployment
  ```bash
  pip install limacharlie
  ```
- **Git**: For version control of your rules
- **Text Editor**: VS Code, Sublime, or similar for reviewing YAML files

---

## Step 1: Set Up Your LimaCharlie Account

### 1.1 Create an Organization

If you haven't already:

1. Navigate to [https://app.limacharlie.io](https://app.limacharlie.io)
2. Create a new account or log in
3. Create an organization (or use an existing one)
4. Note your **Organization ID (OID)** - you'll find this in the URL or under Settings

### 1.2 Generate an API Key

You need an API key to use the conversion tools:

1. In the LimaCharlie web interface, navigate to **Access Management** → **REST API**
2. Click **Create API Key**
3. Give it a descriptive name (e.g., `rule-migration`)
4. Select appropriate permissions:
   - **Minimum required**: `dr.get`, `dr.set` (for D&R rules)
   - **Recommended**: Also enable `sensor.get`, `org.get` for verification
5. Click **Create**
6. **IMPORTANT**: Copy and save your API key immediately - you won't be able to see it again
7. Save your key in a secure location (password manager, environment variable, etc.)

### 1.3 Verify API Access

Test your API credentials:

```bash
# Using curl
curl -X POST "https://jwt.limacharlie.io" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "oid=YOUR_OID&secret=YOUR_API_KEY"
```

You should receive a JWT token in response.

---

## Step 2: Configure Data Ingestion

**CRITICAL**: The AI conversion tools rely on understanding the structure of your data. You MUST configure data ingestion BEFORE converting rules.

### 2.1 Understand LimaCharlie Platforms

LimaCharlie ingests data through:

- **Sensors**: Agents installed on endpoints (Windows, macOS, Linux, Chrome)
- **Adapters**: Connectors for cloud services and third-party platforms
- **External Logs**: Syslog, custom webhooks, and integrations

### 2.2 Choose Your Integration Method

Based on your source platform:

#### For EDR/Endpoint Platforms (CrowdStrike, Carbon Black, Microsoft Defender)

1. Navigate to **Adapters** in the LimaCharlie UI
2. Find your platform adapter (e.g., "CrowdStrike Falcon Cloud")
3. Follow the configuration wizard
4. Provide required credentials (API keys, client IDs, etc.)
5. Select the event types you want to ingest

**Example: CrowdStrike Setup**
```yaml
# Configuration for CrowdStrike adapter
platform: crowdstrike
credentials:
  client_id: YOUR_CLIENT_ID
  client_secret: YOUR_CLIENT_SECRET
event_types:
  - DetectionSummaryEvent
  - IncidentSummaryEvent
  - ProcessExecutionEvent
```

#### For Identity/Access Platforms (Okta, Duo, Azure AD)

1. Navigate to **Adapters** → **Identity & Access**
2. Select your platform
3. Configure OAuth/API credentials
4. Enable log streaming
5. Verify events are flowing

**Example: Okta Setup**
```yaml
platform: okta
credentials:
  domain: your-domain.okta.com
  api_token: YOUR_API_TOKEN
log_types:
  - authentication
  - authorization
  - user_lifecycle
```

#### For SIEM/Log Platforms (Splunk, Elastic, Sigma rules)

If migrating Sigma rules or rules from a SIEM:

1. **Identify the original data source** (Windows Event Logs, Syslog, cloud logs)
2. **Set up the appropriate adapter** for that source
3. **Verify data schema matches** your rule expectations

**Example: Windows Event Logs**
```yaml
platform: windows
collection_method: sensor  # LimaCharlie Windows sensor
event_types:
  - NEW_PROCESS
  - NETWORK_CONNECTIONS
  - FILE_MODIFIED
  - REGISTRY_MODIFIED
```

### 2.3 Verify Data Ingestion

**CRITICAL CHECKPOINT**: Before proceeding, ensure data is flowing:

1. Navigate to **Timeline** in the LimaCharlie UI
2. Verify you see events from your configured platform
3. Examine event structure - note key field names
4. Wait at least 5-10 minutes for sufficient data collection

#### Verification Checklist

- [ ] Events visible in Timeline
- [ ] Event types match your rule targets
- [ ] At least 100+ events collected
- [ ] Event schema looks correct (has expected fields)

**Example Check via CLI:**
```bash
# List recent events
limacharlie events --platform YOUR_PLATFORM --limit 10
```

### 2.4 Document Your Platform Configuration

Create a simple document noting:

```markdown
Platform Name: okta
Adapter Type: Identity & Access
Event Types Ingested:
  - authentication.login
  - authentication.failed_login
  - user.session.start
Data Collection Start: 2025-01-15 14:30 UTC
Sample Event Fields: user.email, client.ip, outcome.result
```

---

## Step 3: Prepare Your Rules

### 3.1 Create a Rules Directory

Organize your source rules in a dedicated directory:

```bash
mkdir -p ~/limacharlie-migration/source-rules
cd ~/limacharlie-migration/source-rules
```

### 3.2 Copy Your Source Rules

Place all your existing rules in this directory. The script supports:

- Individual rule files (any text format: `.yaml`, `.yml`, `.json`, `.txt`, `.spl`, `.kql`, etc.)
- One rule per file recommended (but multi-rule files will be processed)
- Original format preserved - AI will interpret the rule logic

**Example Directory Structure:**
```
source-rules/
├── suspicious_login_from_impossible_travel.yaml
├── brute_force_detection.json
├── privilege_escalation_attempt.txt
├── malware_execution_detection.spl
└── credential_dumping.yml
```

### 3.3 Note Your Source Platform

For each set of rules, note the **target platform** (not the rule language):

- If converting Splunk rules that detect **Okta events** → Platform: `okta`
- If converting Sigma rules that detect **Windows events** → Platform: `windows`
- If converting CrowdStrike rules → Platform: `crowdstrike`

This helps the AI understand the data schema.

---

## Step 4: Run the Conversion Script

### 4.1 Install Dependencies

```bash
# Install Python dependencies
pip install requests pyyaml
```

### 4.2 Download the Conversion Script

```bash
# Download convert_rules.py
curl -O https://[DISTRIBUTION_URL]/convert_rules.py
# Or clone from repository
# git clone https://github.com/[REPO]/limacharlie-migration.git
```

### 4.3 Run the Script

Execute the conversion script:

```bash
python convert_rules.py
```

### 4.4 Follow the Interactive Prompts

The script will ask for:

1. **LimaCharlie Organization ID (OID)**
   ```
   Enter your LimaCharlie Organization ID (OID): 8b7a9c2d-1234-5678-9abc-def012345678
   ```

2. **LimaCharlie API Key**
   ```
   Enter your LimaCharlie API Key: api_key_abcdef1234567890
   ```

3. **Source Platform Name**
   ```
   Enter the source platform name (e.g., okta, crowdstrike, windows): okta
   ```

4. **Rules Directory Path**
   ```
   Enter the path to your rules directory: /home/user/limacharlie-migration/source-rules
   ```

5. **Data Ingestion Confirmation**
   ```
   Have you set up the 'okta' platform/adapter in LimaCharlie and verified data is being ingested? (yes/no): yes
   ```

### 4.5 Monitor Conversion Progress

The script will:

- Display progress for each file
- Show conversion status in real-time
- Report errors if they occur (but continue processing)

**Example Output:**
```
========================================
LimaCharlie Rule Conversion Tool
========================================

Discovering MCP tools...
✓ Found generate_dr_rule_detection
✓ Found generate_dr_rule_respond

Processing rules from: /home/user/limacharlie-migration/source-rules
Output directory: /home/user/limacharlie-migration/source-rules/output

Converting rules:
[1/5] suspicious_login_from_impossible_travel.yaml ... ✓ Success
[2/5] brute_force_detection.json ... ✓ Success
[3/5] privilege_escalation_attempt.txt ... ✗ Error (see report)
[4/5] malware_execution_detection.spl ... ✓ Success
[5/5] credential_dumping.yml ... ✓ Success

========================================
Conversion Complete!
Converted: 4/5 rules
Failed: 1/5 rules
See output/report.txt for details
========================================
```

### 4.6 Review the Output

Check the `output/` directory:

```bash
cd source-rules/output
ls -la
```

You should see:
- Converted YAML files (one per input file)
- `report.txt` with detailed conversion summary

---

## Step 5: Review and Test Converted Rules

### 5.1 Examine Converted Rules

Open one of the converted YAML files:

```yaml
# output/suspicious_login_from_impossible_travel.yaml
detect:
  op: and
  event: authentication.login
  rules:
    - op: is
      path: event/outcome/result
      value: SUCCESS
    - op: exists
      path: event/security_context/is_suspicious
    - op: is
      path: event/security_context/is_suspicious
      value: true

respond:
  - action: report
    name: Suspicious Login - Impossible Travel Detected
    metadata:
      severity: high
      category: credential_access
      platform: okta
  - action: add tag
    tag: suspicious_authentication
    ttl: 86400
```

### 5.2 Validate YAML Syntax

Use a YAML validator to check syntax:

```bash
# Using Python
python -c "import yaml; yaml.safe_load(open('output/suspicious_login_from_impossible_travel.yaml'))"

# Using yamllint (if installed)
yamllint output/suspicious_login_from_impossible_travel.yaml
```

### 5.3 Test Rules with Historical Data

Use LimaCharlie's Replay service to test against historical events:

#### Method 1: Using the Web UI

1. Navigate to **Detection** → **D&R Rules** in LimaCharlie
2. Click **Test Rule**
3. Paste your converted rule YAML
4. Select **Replay** mode
5. Choose a time range (last 24 hours, last 7 days, etc.)
6. Click **Run Test**
7. Review matches and false positives

#### Method 2: Using the CLI

```bash
# Validate rule syntax
limacharlie replay --validate --rule-content output/suspicious_login_from_impossible_travel.yaml

# Test against last 24 hours of events
limacharlie replay \
  --rule-content output/suspicious_login_from_impossible_travel.yaml \
  --entire-org \
  --last-seconds 86400
```

### 5.4 Review Test Results

Examine the output:

- **True Positives**: Expected detections ✓
- **False Positives**: Unexpected matches - may need tuning ✗
- **False Negatives**: Known bad events not caught - needs adjustment ✗

### 5.5 Tune Rules as Needed

If you find issues, manually edit the YAML:

**Common Adjustments:**

- **Too many false positives**: Add more specific conditions
  ```yaml
  # Add exclusions
  - op: not
    rules:
      - op: contains
        path: event/user/email
        value: service-account@
  ```

- **Missing detections**: Broaden conditions or check event paths
  ```yaml
  # Use wildcards or broader matching
  - op: matches
    path: event/*/suspicious_flag
    value: true
  ```

- **Performance issues**: Add early-fail conditions
  ```yaml
  # Put most selective rules first
  op: and
  rules:
    - op: is  # Fastest check first
      path: event/type
      value: authentication
    - op: contains  # Then more expensive checks
      path: event/details/raw_data
      value: malicious_pattern
  ```

---

## Step 6: Deploy Rules to Production

### 6.1 Choose Deployment Method

#### Option A: Web UI (Recommended for Beginners)

1. Navigate to **Detection** → **D&R Rules**
2. Click **Add Rule**
3. Paste your YAML content
4. Give the rule a name
5. Optionally add tags and metadata
6. Click **Save**

#### Option B: LimaCharlie CLI

```bash
# Add a single rule
limacharlie dr add \
  --rule-name "Suspicious Login Detection" \
  --rule-file output/suspicious_login_from_impossible_travel.yaml

# Add multiple rules at once
for file in output/*.yaml; do
  rulename=$(basename "$file" .yaml)
  limacharlie dr add --rule-name "$rulename" --rule-file "$file"
done
```

#### Option C: Infrastructure as Code (Advanced)

Create a git repository with your rules:

```yaml
# config/dr-rules.yaml
rules:
  - name: suspicious-login-impossible-travel
    file: rules/suspicious_login_from_impossible_travel.yaml
  - name: brute-force-detection
    file: rules/brute_force_detection.yaml
```

Use LimaCharlie's Git Sync extension or automation to deploy.

### 6.2 Enable Rules Gradually

For large rule sets, enable incrementally:

1. **Week 1**: Deploy 20% of rules, monitor for issues
2. **Week 2**: Deploy another 30%, tune based on feedback
3. **Week 3**: Deploy remaining 50%

### 6.3 Monitor Rule Performance

After deployment, monitor:

- **Detection volume**: Are you getting expected alerts?
- **False positive rate**: Too many false alarms?
- **Resource usage**: Rules impacting performance?

Check in the LimaCharlie UI:

- **Detections** → View all triggered alerts
- **Analytics** → Rule performance metrics

---

## Troubleshooting

### Conversion Script Errors

#### Error: "Failed to connect to MCP server"

**Cause**: Network issue or incorrect API credentials

**Solution**:
1. Verify API key and OID are correct
2. Check network connectivity to `https://mcp.limacharlie.io`
3. Ensure API key has proper permissions

```bash
# Test connectivity
curl -v https://mcp.limacharlie.io/mcp

# Verify API credentials
curl -X POST "https://jwt.limacharlie.io" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "oid=YOUR_OID&secret=YOUR_API_KEY"
```

#### Error: "Tool not found: generate_dr_rule_detection"

**Cause**: MCP server may not have AI tools enabled or requires GOOGLE_API_KEY

**Solution**:
1. Check if you have AI features enabled in your LimaCharlie org
2. Contact LimaCharlie support to enable AI features
3. Verify your subscription includes AI-powered tools

#### Error: "Invalid rule format"

**Cause**: Source rule has syntax the AI couldn't interpret

**Solution**:
1. Check the source rule file for obvious syntax errors
2. Ensure the file is readable text
3. Try adding comments explaining the rule's intent
4. Manually review and convert the rule

#### Error: "No data found for platform 'X'"

**Cause**: Platform not configured or no data ingested yet

**Solution**:
1. Return to [Step 2](#step-2-configure-data-ingestion)
2. Verify adapter/sensor is configured
3. Check Timeline for events
4. Wait 10-15 minutes for data collection

### Rule Testing Issues

#### Test Returns No Matches (False Negatives)

**Possible causes**:

1. **Event paths incorrect**: Field names don't match your data
   - **Fix**: Check actual event structure in Timeline
   - Use LimaCharlie Query Language (LCQL) to explore event schema:
     ```sql
     SELECT * FROM events WHERE event_type = 'authentication.login' LIMIT 10
     ```

2. **Event type mismatch**: Rule looking for wrong event type
   - **Fix**: Update `event:` field to match actual events

3. **Data not available**: Test range doesn't include matching events
   - **Fix**: Extend test time range or trigger test events

#### Test Returns Too Many Matches (False Positives)

**Possible causes**:

1. **Rule too broad**: Conditions not specific enough
   - **Fix**: Add more restrictive conditions
   ```yaml
   # Before (too broad)
   - op: exists
     path: event/user

   # After (more specific)
   - op: and
     rules:
       - op: exists
         path: event/user
       - op: not
         rules:
           - op: ends with
             path: event/user/email
             value: "@trusted-domain.com"
   ```

2. **Missing exclusions**: Legitimate activity triggering rule
   - **Fix**: Add exclusion rules for known-good patterns

### Deployment Issues

#### Rule Syntax Error After Deployment

**Cause**: YAML indentation or syntax error

**Solution**:
```bash
# Validate YAML before deployment
python -c "import yaml; print(yaml.safe_load(open('rule.yaml')))"

# Use limacharlie CLI validation
limacharlie replay --validate --rule-content rule.yaml
```

#### Rule Not Triggering in Production

**Cause**: Event stream stopped, rule disabled, or logic issue

**Solution**:
1. Check rule is enabled in UI
2. Verify events still flowing (Timeline)
3. Test rule with Replay again
4. Check rule priority/ordering

---

## Appendix

### A. Supported Source Platforms

The conversion tool works best with rules targeting these platforms:

#### Identity & Access
- Okta
- Duo
- Azure Active Directory
- Google Workspace
- OneLogin

#### Endpoint/EDR
- CrowdStrike
- Carbon Black
- Microsoft Defender
- SentinelOne
- Windows (native)
- macOS (native)
- Linux (native)

#### Cloud Platforms
- AWS CloudTrail
- Azure Activity Logs
- Google Cloud Audit Logs

#### Network & Logs
- Syslog
- Windows Event Logs
- Custom JSON logs

### B. D&R Rule Format Reference

LimaCharlie D&R rules have two main sections:

#### Detection Section

```yaml
detect:
  event: EVENT_TYPE           # Required: Event to monitor
  op: OPERATOR                # Required: Logical operator
  path: event/FIELD/PATH      # Optional: Path to field
  value: EXPECTED_VALUE       # Optional: Expected value
  rules:                      # Optional: Nested conditions
    - op: ...
      path: ...
```

**Common Operators:**
- `and`, `or`: Combine multiple rules
- `is`, `is not`: Exact match
- `contains`, `starts with`, `ends with`: String matching
- `exists`: Field presence check
- `matches`: Regex matching
- `is greater than`, `is lower than`: Numeric comparison

#### Response Section

```yaml
respond:
  - action: report
    name: "Alert Name"
    metadata:
      severity: high
      category: credential_access
  - action: add tag
    tag: suspicious_activity
    ttl: 86400
  - action: task
    command: isolate
```

**Common Actions:**
- `report`: Generate detection alert
- `add tag`: Tag the sensor
- `task`: Execute endpoint command
- `webhook`: Send to external system

### C. Additional Resources

- **LimaCharlie Documentation**: [https://docs.limacharlie.io](https://docs.limacharlie.io)
- **D&R Rule Examples**: [https://docs.limacharlie.io/docs/detection-and-response-examples](https://docs.limacharlie.io/docs/detection-and-response-examples)
- **Community Rules**: [https://github.com/refractionPOINT/rules](https://github.com/refractionPOINT/rules)
- **LimaCharlie Community**: [https://community.limacharlie.com](https://community.limacharlie.com)
- **MCP Server Docs**: [https://docs.limacharlie.io/docs/mcp-server](https://docs.limacharlie.io/docs/mcp-server)

### D. Script Command-Line Options

The conversion script supports command-line arguments for automation:

```bash
python convert_rules.py \
  --oid "YOUR_OID" \
  --api-key "YOUR_API_KEY" \
  --platform "okta" \
  --rules-dir "/path/to/rules" \
  --output-dir "/path/to/output" \
  --skip-confirmation
```

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check the report.txt**: Detailed error messages
2. **LimaCharlie Community**: [https://community.limacharlie.com](https://community.limacharlie.com)
3. **GitHub Issues**: [Report issues or request features]
4. **LimaCharlie Support**: Contact via your organization dashboard

---

**Last Updated**: January 2025
**Script Version**: 1.0.0
