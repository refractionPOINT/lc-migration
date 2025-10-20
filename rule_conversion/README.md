# LimaCharlie Migration Tools

Various tools and guides to help with migrating to LimaCharlie.

## Rule Migration Toolkit

Automatically convert security detection rules from various platforms (Splunk, Elastic, Sigma, CrowdStrike, Okta, etc.) into LimaCharlie Detection & Response (D&R) rules using AI-powered conversion.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure LimaCharlie CLI

If you already have the LimaCharlie CLI installed and configured, **the script will auto-detect your credentials**:

```bash
# Configure LimaCharlie CLI (if not already done)
pip install limacharlie
limacharlie login
```

Otherwise, you'll be prompted to enter your credentials manually.

### 3. Prepare Your Rules

Place your existing detection rules in a directory:

```bash
mkdir -p my-rules
# Copy your existing rules into my-rules/
```

### 4. Run the Conversion

```bash
python convert_rules.py
```

**If you have LimaCharlie CLI configured**, the script will detect and use those credentials:
```
✓ Found LimaCharlie credentials from ~/.limacharlie
  Organization ID: 8b7a9c2d-xxxx
  API Key: api_****7890

Use these credentials? (yes/no) [yes]:
```

Otherwise, follow the interactive prompts to:
- Enter your LimaCharlie credentials (API key and Organization ID)
- Specify your source platform (e.g., `okta`, `crowdstrike`, `windows`)
- Point to your rules directory
- Confirm you've set up data ingestion

### 5. Review the Results

Converted rules will be in `my-rules/output/`:

```bash
ls my-rules/output/
# suspicious_login.yaml
# brute_force.yaml
# report.txt  ← Detailed conversion report
```

## Complete Documentation

For detailed step-by-step instructions, see **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)**

The guide covers:
- Setting up your LimaCharlie account
- Configuring data ingestion for your platform
- Running the conversion process
- Testing and deploying converted rules
- Troubleshooting common issues

## Features

- **Credential Auto-Detection**: Automatically uses credentials from LimaCharlie CLI or environment variables
- **AI-Powered Conversion**: Uses LimaCharlie's MCP server tools to intelligently convert rules
- **Platform-Aware**: Adapts to your specific data source (Okta, CrowdStrike, Windows, etc.)
- **Parallel Processing**: Convert up to 20 rules concurrently for significantly faster batch processing
- **Batch Processing**: Convert entire rule libraries at once
- **Error Resilience**: Continues processing even if some rules fail
- **Detailed Reporting**: Generates comprehensive reports with success/failure details
- **Interactive & Automated**: Supports both interactive and command-line modes

## Command-Line Usage

For automation and CI/CD integration:

```bash
python convert_rules.py \
  --oid "your-org-id" \
  --api-key "your-api-key" \
  --platform "okta" \
  --rules-dir "/path/to/rules" \
  --parallel-workers 20 \
  --skip-confirmation
```

### Arguments

- `--oid`: LimaCharlie Organization ID
- `--api-key`: LimaCharlie API Key
- `--platform`: Source platform name (e.g., okta, crowdstrike, windows)
- `--rules-dir`: Directory containing source rules
- `--output-dir`: Output directory (default: rules-dir/output)
- `--parallel-workers`: Number of parallel workers (default: 20, min: 1, max: 50)
- `--skip-confirmation`: Skip the data ingestion confirmation prompt
- `--endpoint`: MCP server endpoint (default: https://mcp.limacharlie.io/mcp)

## Example Conversion

**Input** (Splunk SPL rule):
```spl
index=okta sourcetype=okta:system action=user.session.start
| where outcome.result="FAILURE"
| stats count by user.email, client.ipAddress
| where count > 5
```

**Output** (LimaCharlie D&R rule):
```yaml
detect:
  op: and
  event: authentication.login
  rules:
    - op: is
      path: event/outcome/result
      value: FAILURE
    - op: exists
      path: event/client/ipAddress

respond:
  - action: report
    name: Multiple Failed Login Attempts Detected
    metadata:
      severity: medium
      category: credential_access
      platform: okta
  - action: add tag
    tag: failed_authentication
    ttl: 86400
```

## Supported Platforms

The conversion tool works with rules targeting:

### Identity & Access
- Okta
- Duo
- Azure Active Directory
- Google Workspace
- OneLogin

### Endpoint/EDR
- CrowdStrike
- Carbon Black
- Microsoft Defender
- SentinelOne
- Windows (native sensors)
- macOS (native sensors)
- Linux (native sensors)

### Cloud Platforms
- AWS CloudTrail
- Azure Activity Logs
- Google Cloud Audit Logs

### Network & Logs
- Syslog
- Windows Event Logs
- Custom JSON logs

## Prerequisites

1. **LimaCharlie Account**: Sign up at [https://app.limacharlie.io](https://app.limacharlie.io)
2. **API Credentials**: Generate an API key from your LimaCharlie organization
3. **Data Ingestion**: Configure the relevant platform/adapter in LimaCharlie BEFORE running conversion
4. **Python 3.8+**: Required to run the conversion script

## Project Structure

```
rule_conversion/
├── README.md                  ← This file
├── MIGRATION_GUIDE.md         ← Detailed step-by-step guide
├── convert_rules.py           ← Main conversion script
├── requirements.txt           ← Python dependencies
└── examples/                  ← Example rules for testing
    ├── okta/
    │   ├── suspicious_login.txt
    │   └── brute_force.yaml
    ├── crowdstrike/
    │   └── malware_detection.json
    └── windows/
        └── privilege_escalation.yml
```

## How It Works

1. **Tool Discovery**: Connects to LimaCharlie MCP server and discovers available AI tools
2. **Rule Reading**: Reads all files from your specified rules directory
3. **AI Conversion**: For each rule (processed in parallel with configurable workers):
   - Sends to `generate_dr_rule_detection` (creates the detection logic)
   - Sends to `generate_dr_rule_respond` (creates the response actions)
4. **YAML Generation**: Combines detect and respond sections into LimaCharlie D&R format
5. **Output**: Writes converted rules to output directory with original filenames
6. **Reporting**: Generates detailed report with success/failure statistics

**Performance**: With parallel processing enabled (default 20 workers), converting 100 rules takes approximately 20x less time compared to sequential processing. For example, 100 rules that take ~2 seconds each will complete in ~20 seconds instead of ~200 seconds.

## Troubleshooting

### Common Issues

**"Failed to connect to MCP server"**
- Verify your API key and Organization ID are correct
- Check network connectivity to https://mcp.limacharlie.io

**"Tool not found: generate_dr_rule_detection"**
- Ensure AI features are enabled in your LimaCharlie organization
- Contact LimaCharlie support to enable AI-powered tools

**"No data found for platform 'X'"**
- You must configure data ingestion BEFORE running conversion
- See MIGRATION_GUIDE.md Step 2 for platform setup instructions

**Rules convert but don't match in production**
- Verify data is flowing in LimaCharlie Timeline
- Check event field names match your actual data schema
- Use LimaCharlie's Replay service to test rules with historical data

For more troubleshooting help, see the [Troubleshooting section](MIGRATION_GUIDE.md#troubleshooting) in the Migration Guide.

## Getting Help

- **Documentation**: [https://docs.limacharlie.io](https://docs.limacharlie.io)
- **Community Forum**: [https://community.limacharlie.com](https://community.limacharlie.com)
- **MCP Server Docs**: [https://docs.limacharlie.io/docs/mcp-server](https://docs.limacharlie.io/docs/mcp-server)

## Contributing

Contributions welcome! If you find issues or have suggestions:

1. Check existing issues
2. Open a new issue with details
3. Submit pull requests with improvements

## License

Apache License 2.0 - See LICENSE file for details

## Version

**Version**: 1.0.0
**Last Updated**: January 2025

## Credits

Built by the LimaCharlie team to help security teams migrate to the LimaCharlie platform.

Powered by the [LimaCharlie MCP Server](https://docs.limacharlie.io/docs/mcp-server) and the [Model Context Protocol](https://modelcontextprotocol.io).
