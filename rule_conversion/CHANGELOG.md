# Changelog

All notable changes to the LimaCharlie Rule Conversion Tool will be documented in this file.

## [1.1.0] - 2025-01-16

### Added

#### Automatic Credential Detection
- **Auto-detect LimaCharlie credentials** from existing SDK/CLI configuration
- Checks credentials in this order:
  1. Command-line arguments (highest priority)
  2. Environment variables (`LC_OID`, `LC_API_KEY`)
  3. LimaCharlie CLI config file (`~/.limacharlie`)
- Displays detected credentials (with masked API key) and asks for user confirmation
- Falls back to manual entry if no credentials found or user declines

#### Enhanced User Experience
- `convert_rules.py`: Shows credential source and asks for confirmation before using
- `verify_setup.py`: Now supports auto-detection, making `--oid` and `--api-key` optional
- API keys are masked for security when displayed (shows only first 4 and last 4 characters)

### Changed

#### Scripts Updated
- **`convert_rules.py`**:
  - Added `load_limacharlie_credentials()` function
  - Added `mask_api_key()` helper function
  - Modified `main()` to attempt credential auto-detection before prompting
  - CLI arguments still override auto-detected credentials

- **`verify_setup.py`**:
  - Added same credential loading functions
  - Changed `--oid` and `--api-key` from required to optional arguments
  - Shows credential source in verification output
  - Provides helpful error message if no credentials found

#### Documentation Updated
- **`README.md`**:
  - Added credential auto-detection as first feature
  - Updated Quick Start with auto-detection workflow
  - Shows example of auto-detection confirmation prompt

- **`QUICKSTART.md`**:
  - Updated prerequisites to mention CLI configuration option
  - Added installation instructions for LimaCharlie CLI
  - Shows both auto-detected and manual credential entry workflows

### Benefits

**For users with LimaCharlie CLI already configured:**
- No need to re-enter credentials
- Seamless workflow - just run `python convert_rules.py`
- Credentials stay secure in `~/.limacharlie` file

**For users without CLI:**
- Behavior unchanged - will prompt for credentials as before
- Can still use command-line arguments
- Can set environment variables for automation

**For CI/CD environments:**
- Can use environment variables (`LC_OID`, `LC_API_KEY`)
- Can still use command-line arguments
- No breaking changes to existing workflows

### Backward Compatibility

✅ **Fully backward compatible** - all existing usage patterns continue to work:
- Command-line arguments still work exactly as before
- Interactive prompts still work if no credentials detected
- Environment variables still work
- No changes to output format or file structure

## [1.0.0] - 2025-01-15

### Initial Release

- AI-powered rule conversion using LimaCharlie MCP server
- Support for multiple source platforms (Okta, CrowdStrike, Windows, Sigma, etc.)
- Batch processing of entire rule directories
- Interactive and command-line modes
- Detailed error reporting
- Comprehensive documentation (Migration Guide, Quick Start, README)
- Example rules for testing
- Setup verification tool
