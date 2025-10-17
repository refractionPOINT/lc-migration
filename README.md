# LimaCharlie Migration Tools

Guides and tools to help with migrating to LimaCharlie from other security platforms.

## Overview

This repository provides resources to assist security teams in migrating their existing security infrastructure, detection rules, and workflows to the LimaCharlie platform. Whether you're migrating from a legacy SIEM, EDR solution, or identity provider, these tools are designed to streamline the transition process.

## Available Migration Tools

### [Rule Conversion](./rule_conversion/)

AI-powered toolkit for converting security detection rules from various platforms to LimaCharlie Detection & Response (D&R) format.

**Supported Source Platforms:**
- **SIEM & Analytics**: Splunk, Elastic, Sigma
- **Endpoint/EDR**: CrowdStrike, Carbon Black, Microsoft Defender, SentinelOne
- **Identity & Access**: Okta, Duo, Azure AD, Google Workspace
- **Cloud Platforms**: AWS CloudTrail, Azure, Google Cloud
- **Custom Sources**: Windows Event Logs, Syslog, JSON logs

**Key Features:**
- AI-powered rule conversion using LimaCharlie's MCP server
- Batch processing for entire rule libraries
- Interactive and CLI modes for automation
- Platform-aware conversion with data schema validation
- Detailed reporting and error handling

**Quick Start:**
```bash
cd rule_conversion
pip install -r requirements.txt
python convert_rules.py
```

See the [Rule Conversion README](./rule_conversion/README.md) for complete documentation.

## Coming Soon

Additional migration tools and guides are planned for:
- Configuration migration helpers
- Data ingestion setup automation
- Response workflow conversion
- Integration mapping guides

## Getting Started

1. **Choose Your Migration Tool**: Start with the component that matches your migration needs
2. **Review Documentation**: Each tool has comprehensive guides and examples
3. **Test First**: Use the tools with sample data before production migration
4. **Get Support**: Visit [LimaCharlie Community](https://community.limacharlie.com) for help

## Prerequisites

Before using these migration tools:

1. **LimaCharlie Account**: Sign up at [app.limacharlie.io](https://app.limacharlie.io)
2. **API Credentials**: Generate an API key from your organization settings
3. **Data Ingestion**: Configure relevant adapters/sensors in LimaCharlie
4. **Python 3.8+**: Required for running migration scripts

## Resources

- **Documentation**: [docs.limacharlie.io](https://docs.limacharlie.io)
- **Community Forum**: [community.limacharlie.com](https://community.limacharlie.com)
- **MCP Server**: [docs.limacharlie.io/docs/mcp-server](https://docs.limacharlie.io/docs/mcp-server)

## Contributing

Contributions are welcome! If you've developed migration tools or guides that would benefit others:

1. Fork this repository
2. Create a feature branch
3. Submit a pull request with your additions

## Support

For questions or issues:
- Check tool-specific documentation in each subdirectory
- Visit the [LimaCharlie Community](https://community.limacharlie.com)
- Open an issue in this repository

## License

MIT License - See LICENSE file for details
