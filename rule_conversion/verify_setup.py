#!/usr/bin/env python3
"""
LimaCharlie Setup Verification Tool

This script verifies that your environment is correctly configured before
running the rule conversion process.

Usage:
    python verify_setup.py --oid YOUR_OID --api-key YOUR_API_KEY --platform okta
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    import requests
except ImportError:
    print("❌ ERROR: 'requests' library not found")
    print("   Install it with: pip install requests")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("❌ ERROR: 'pyyaml' library not found")
    print("   Install it with: pip install pyyaml")
    sys.exit(1)


def load_limacharlie_credentials() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Auto-detect LimaCharlie credentials from SDK/CLI configuration.

    Checks in order:
    1. Environment variables (LC_OID, LC_API_KEY, LC_UID)
    2. ~/.limacharlie file (default credentials)

    Returns:
        Tuple of (oid, api_key, source) where source indicates where credentials were found,
        or (None, None, None) if not found
    """
    # Check environment variables first
    env_oid = os.environ.get('LC_OID')
    env_api_key = os.environ.get('LC_API_KEY')

    if env_oid and env_api_key:
        return env_oid, env_api_key, "environment variables"

    # Check ~/.limacharlie file
    config_file = Path.home() / '.limacharlie'

    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            if config:
                # Check for default/top-level credentials
                oid = config.get('oid')
                api_key = config.get('api_key')

                if oid and api_key:
                    return oid, api_key, "~/.limacharlie"
        except Exception as e:
            # If there's an error reading the file, silently continue
            pass

    return None, None, None


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for display, showing only first 4 and last 4 characters.

    Args:
        api_key: The API key to mask

    Returns:
        Masked API key string
    """
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"


def check_python_version():
    """Verify Python version is 3.8+."""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False


def check_dependencies():
    """Verify required Python packages are installed."""
    print("\n🔍 Checking dependencies...")

    success = True

    # Check requests
    try:
        import requests
        print(f"✅ requests {requests.__version__}")
    except ImportError:
        print("❌ requests not installed")
        success = False

    # Check pyyaml
    try:
        import yaml
        print(f"✅ pyyaml (yaml module available)")
    except ImportError:
        print("❌ pyyaml not installed")
        success = False

    return success


def check_api_credentials(oid, api_key):
    """Verify LimaCharlie API credentials."""
    print("\n🔍 Checking LimaCharlie API credentials...")

    try:
        response = requests.post(
            "https://jwt.limacharlie.io",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"oid={oid}&secret={api_key}",
            timeout=10
        )

        if response.status_code == 200:
            print("✅ API credentials valid (JWT token obtained)")
            return True
        else:
            print(f"❌ API credentials invalid (HTTP {response.status_code})")
            print(f"   Response: {response.text[:200]}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to verify credentials: {e}")
        return False


def check_mcp_server():
    """Verify MCP server is accessible."""
    print("\n🔍 Checking MCP server accessibility...")

    try:
        response = requests.get("https://mcp.limacharlie.io", timeout=10)
        print(f"✅ MCP server accessible (HTTP {response.status_code})")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach MCP server: {e}")
        return False


def check_mcp_tools(oid, api_key):
    """Verify MCP tools are available."""
    print("\n🔍 Checking MCP tools availability...")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {api_key}:{oid}",
        "x-lc-oid": oid
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }

    try:
        response = requests.post(
            "https://mcp.limacharlie.io/mcp",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ MCP server error (HTTP {response.status_code})")
            print(f"   Response: {response.text[:200]}")
            return False

        data = response.json()

        if "error" in data:
            print(f"❌ MCP error: {data['error'].get('message')}")
            return False

        tools = data.get("result", {}).get("tools", [])

        # Look for required tools
        detection_tool = None
        respond_tool = None

        for tool in tools:
            if tool.get("name") == "generate_dr_rule_detection":
                detection_tool = tool
            elif tool.get("name") == "generate_dr_rule_respond":
                respond_tool = tool

        if detection_tool:
            print("✅ generate_dr_rule_detection available")
        else:
            print("❌ generate_dr_rule_detection NOT FOUND")

        if respond_tool:
            print("✅ generate_dr_rule_respond available")
        else:
            print("❌ generate_dr_rule_respond NOT FOUND")

        if detection_tool and respond_tool:
            print(f"\n📊 Total MCP tools available: {len(tools)}")
            return True
        else:
            print("\n⚠️  WARNING: Required AI tools not found")
            print("   This may indicate:")
            print("   1. AI features not enabled for your organization")
            print("   2. Insufficient API key permissions")
            print("   3. GOOGLE_API_KEY not configured on MCP server")
            print("\n   Contact LimaCharlie support to enable AI features.")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to check MCP tools: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify LimaCharlie environment setup for rule conversion"
    )
    parser.add_argument("--oid", help="LimaCharlie Organization ID (auto-detected if not provided)")
    parser.add_argument("--api-key", help="LimaCharlie API Key (auto-detected if not provided)")
    parser.add_argument("--platform", help="Platform name (for informational purposes)")

    args = parser.parse_args()

    print("=" * 70)
    print("LIMACHARLIE SETUP VERIFICATION")
    print("=" * 70)

    # Auto-detect credentials if not provided
    oid = args.oid
    api_key = args.api_key
    creds_source = "command-line arguments" if oid and api_key else None

    if not oid or not api_key:
        detected_oid, detected_api_key, detected_source = load_limacharlie_credentials()

        if detected_oid and detected_api_key:
            if not oid:
                oid = detected_oid
            if not api_key:
                api_key = detected_api_key
            if not creds_source:
                creds_source = detected_source

    if not oid or not api_key:
        print("\n❌ ERROR: No credentials found")
        print("\nPlease either:")
        print("  1. Run 'limacharlie login' to configure credentials, or")
        print("  2. Set LC_OID and LC_API_KEY environment variables, or")
        print("  3. Provide --oid and --api-key arguments")
        print("\nExample:")
        print("  python verify_setup.py --oid YOUR_OID --api-key YOUR_API_KEY")
        print("=" * 70)
        sys.exit(1)

    # Show credential source
    print(f"\n✓ Using credentials from: {creds_source}")
    print(f"  Organization ID: {oid}")
    print(f"  API Key: {mask_api_key(api_key)}")

    if args.platform:
        print(f"\nTarget Platform: {args.platform}")

    print()

    # Run all checks
    checks = []

    checks.append(("Python Version", check_python_version()))
    checks.append(("Dependencies", check_dependencies()))
    checks.append(("API Credentials", check_api_credentials(oid, api_key)))
    checks.append(("MCP Server", check_mcp_server()))
    checks.append(("MCP Tools", check_mcp_tools(oid, api_key)))

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")

    all_passed = all(result for _, result in checks)

    print("\n" + "=" * 70)

    if all_passed:
        print("🎉 All checks passed! You're ready to convert rules.")
        print("\nNext steps:")
        print("  1. Ensure your platform/adapter is configured in LimaCharlie")
        print("  2. Verify data is flowing in the Timeline")
        print("  3. Run: python convert_rules.py")
        print("=" * 70)
        sys.exit(0)
    else:
        print("⚠️  Some checks failed. Please fix the issues above before converting rules.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Verify API credentials in LimaCharlie web UI")
        print("  - Contact LimaCharlie support for AI feature enablement")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
