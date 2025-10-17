# Quick Start Guide

Get up and running with LimaCharlie rule conversion in 5 minutes.

## Prerequisites Checklist

- [ ] LimaCharlie account created at [app.limacharlie.io](https://app.limacharlie.io)
- [ ] **Either** LimaCharlie CLI configured (`limacharlie login`) **OR** API key/OID available
- [ ] Platform adapter configured (e.g., Okta, CrowdStrike, Windows)
- [ ] Data flowing in Timeline (verify events are being ingested)

## Installation

```bash
# Clone or download the conversion tool
cd rule_conversion

# Install dependencies
pip install -r requirements.txt

# Optional: Configure LimaCharlie CLI for auto-detection
pip install limacharlie
limacharlie login
```

**Note**: If you have the LimaCharlie CLI configured, the script will automatically detect and use your credentials. No need to re-enter them!

## 5-Minute Workflow

### 1. Prepare Rules Directory (30 seconds)

```bash
mkdir my-rules
# Copy your existing rules into my-rules/
cp /path/to/your/rules/* my-rules/
```

### 2. Run Conversion (3 minutes)

```bash
python convert_rules.py
```

**If you have LimaCharlie CLI configured:**

```
✓ Found LimaCharlie credentials from ~/.limacharlie
  Organization ID: 8b7a9c2d-xxxx
  API Key: api_****7890

Use these credentials? (yes/no) [yes]: yes
✓ Using detected credentials

Enter the source platform name: okta
Enter the rules directory path: ./my-rules
Have you completed data ingestion setup? (yes/no): yes
```

**Otherwise, follow the prompts:**

```
Enter your LimaCharlie Organization ID (OID): 8b7a9c2d-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Enter your LimaCharlie API Key: api_xxxxxxxxxxxxx
Enter the source platform name: okta
Enter the rules directory path: ./my-rules
Have you completed data ingestion setup? (yes/no): yes
```

**Wait for conversion:**
```
Discovering MCP tools...
✓ Found generate_dr_rule_detection
✓ Found generate_dr_rule_respond

Converting rules:
[1/3] suspicious_login.yaml ... ✓ Success
[2/3] brute_force.yaml ... ✓ Success
[3/3] malware.json ... ✓ Success

Conversion Complete!
Converted: 3/3 rules
```

### 3. Review Output (1 minute)

```bash
# Check converted rules
ls my-rules/output/

# View a converted rule
cat my-rules/output/suspicious_login.yaml

# Check the conversion report
cat my-rules/output/report.txt
```

### 4. Test & Deploy (30 seconds)

**Option A: Web UI**
1. Open LimaCharlie web app
2. Navigate to Detection → D&R Rules
3. Click "Add Rule"
4. Paste the YAML from output file
5. Save

**Option B: CLI**
```bash
limacharlie dr add \
  --rule-name "Suspicious Login" \
  --rule-file my-rules/output/suspicious_login.yaml
```

## Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| "Failed to connect to MCP server" | Check API key and OID are correct |
| "Tool not found" | Ensure AI features enabled in your org |
| "No data found for platform" | Verify adapter configured and data flowing in Timeline |
| Rules don't match | Check event field names in Timeline match rule expectations |

## Command-Line Mode (Advanced)

Skip prompts for automation:

```bash
python convert_rules.py \
  --oid "your-oid" \
  --api-key "your-key" \
  --platform "okta" \
  --rules-dir "./my-rules" \
  --skip-confirmation
```

## Test with Examples

Try the included example rules first:

```bash
python convert_rules.py \
  --oid "your-oid" \
  --api-key "your-key" \
  --platform "okta" \
  --rules-dir "./examples/okta" \
  --skip-confirmation
```

## Next Steps

- Read [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for comprehensive documentation
- Test converted rules with LimaCharlie's Replay service
- Tune rules based on false positives
- Deploy to production incrementally

## Getting Help

- Documentation: https://docs.limacharlie.io
- Community: https://community.limacharlie.com
- MCP Server: https://docs.limacharlie.io/docs/mcp-server

---

**Ready to migrate your entire rule library? See the full [Migration Guide](MIGRATION_GUIDE.md).**
