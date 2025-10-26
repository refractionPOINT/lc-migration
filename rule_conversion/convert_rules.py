#!/usr/bin/env python3
"""
LimaCharlie Rule Conversion Tool

This script converts security detection rules from various platforms (Splunk, Elastic,
Sigma, CrowdStrike, Okta, etc.) into LimaCharlie Detection & Response (D&R) rules
using the LimaCharlie MCP server's AI-powered conversion tools.

Author: LimaCharlie
Version: 1.0.0
License: Apache License 2.0
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not found. Install it with: pip install requests")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: 'pyyaml' library not found. Install it with: pip install pyyaml")
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
            # (we'll fall back to manual entry)
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


class MCPClient:
    """Client for communicating with the LimaCharlie MCP server using JSON-RPC 2.0."""

    def __init__(self, api_key: str, oid: str, endpoint: str = "https://mcp.limacharlie.io/mcp"):
        """
        Initialize the MCP client.

        Args:
            api_key: LimaCharlie API key
            oid: LimaCharlie Organization ID
            endpoint: MCP server endpoint URL
        """
        self.api_key = api_key
        self.oid = oid
        self.endpoint = endpoint
        self.session_id = None
        self.request_id = 0

    def _get_headers(self) -> Dict[str, str]:
        """Build HTTP headers for MCP requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.api_key}:{self.oid}",
            "x-lc-oid": self.oid
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _make_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a JSON-RPC 2.0 request to the MCP server.

        Args:
            method: The JSON-RPC method name (e.g., "tools/list", "tools/call")
            params: Optional parameters for the method

        Returns:
            The JSON-RPC result or raises an exception
        """
        self.request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }

        try:
            response = requests.post(
                self.endpoint,
                headers=self._get_headers(),
                json=payload,
                timeout=300  # 5 minutes timeout for AI operations
            )
            response.raise_for_status()

            # Check for session ID in response
            if "Mcp-Session-Id" in response.headers and not self.session_id:
                self.session_id = response.headers["Mcp-Session-Id"]

            # Handle JSON response
            if response.headers.get("Content-Type", "").startswith("application/json"):
                data = response.json()

                if "error" in data:
                    error = data["error"]
                    raise Exception(f"MCP Error {error.get('code')}: {error.get('message')}")

                return data.get("result", {})

            # Handle SSE streaming response
            elif response.headers.get("Content-Type", "").startswith("text/event-stream"):
                # For SSE, we need to parse the stream
                # This is a simplified handler - full implementation would parse SSE format
                result = self._parse_sse_response(response.text)
                return result

            else:
                raise Exception(f"Unexpected content type: {response.headers.get('Content-Type')}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to MCP server: {e}")

    def _parse_sse_response(self, sse_text: str) -> Dict:
        """
        Parse Server-Sent Events response.

        Args:
            sse_text: Raw SSE response text

        Returns:
            Parsed result dictionary
        """
        # SSE format: "data: {json}\n\n"
        # This is a simplified parser
        lines = sse_text.strip().split('\n')
        for line in lines:
            if line.startswith('data: '):
                data_json = line[6:]  # Remove "data: " prefix
                try:
                    data = json.loads(data_json)
                    if "result" in data:
                        return data["result"]
                    elif "error" in data:
                        error = data["error"]
                        raise Exception(f"MCP Error: {error.get('message')}")
                except json.JSONDecodeError:
                    continue
        return {}

    def list_tools(self) -> List[Dict]:
        """
        List all available tools from the MCP server.

        Returns:
            List of tool definitions with name, description, and inputSchema
        """
        result = self._make_request("tools/list")
        return result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        params = {
            "name": tool_name,
            "arguments": arguments
        }
        result = self._make_request("tools/call", params)
        return result


class RuleConverter:
    """Main class for converting rules using the LimaCharlie MCP server."""

    def __init__(self, mcp_client: MCPClient, platform: str):
        """
        Initialize the rule converter.

        Args:
            mcp_client: Initialized MCP client
            platform: Source platform name (e.g., 'okta', 'crowdstrike')
        """
        self.mcp = mcp_client
        self.platform = platform
        self.tools_cache = None
        self.conversion_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": []
        }
        self.stats_lock = threading.Lock()

    def discover_tools(self) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Discover the D&R rule generation tools from the MCP server.

        Returns:
            Tuple of (detection_tool, respond_tool) dictionaries
        """
        print("Discovering MCP tools...")

        try:
            tools = self.mcp.list_tools()
            self.tools_cache = tools

            detection_tool = None
            respond_tool = None

            for tool in tools:
                if tool.get("name") == "generate_dr_rule_detection":
                    detection_tool = tool
                    print("✓ Found generate_dr_rule_detection")
                elif tool.get("name") == "generate_dr_rule_respond":
                    respond_tool = tool
                    print("✓ Found generate_dr_rule_respond")

            if not detection_tool:
                print("✗ Warning: generate_dr_rule_detection tool not found")
            if not respond_tool:
                print("✗ Warning: generate_dr_rule_respond tool not found")

            return detection_tool, respond_tool

        except Exception as e:
            print(f"✗ Error discovering tools: {e}")
            return None, None

    def convert_rule(self, rule_content: str, rule_filename: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Convert a single rule to LimaCharlie D&R format.

        Args:
            rule_content: Original rule content as string
            rule_filename: Original filename for context

        Returns:
            Tuple of (detect_yaml, respond_yaml, error_message) where error_message is None on success
        """
        try:
            # Build natural language query for detection generation
            # The MCP tools expect a simple "query" parameter with a natural language description
            detection_query = f"""Convert this {self.platform} security detection rule to LimaCharlie D&R detection format.

Rule name: {rule_filename}
Platform: {self.platform}

Original rule:
{rule_content}

Generate the detection component in LimaCharlie D&R YAML format."""

            # Call detection generation tool with correct parameter
            print(f"  → Generating detection component...")
            detection_result = self.mcp.call_tool("generate_dr_rule_detection", {"query": detection_query})

            # Extract YAML from result - tool returns dict with "detection" or "error" key
            detect_yaml = self._extract_yaml(detection_result)

            if not detect_yaml:
                raise Exception("Detection tool returned no YAML content")

            # Build natural language query for response generation
            respond_query = f"""Convert this {self.platform} security detection rule to LimaCharlie D&R response format.

Rule name: {rule_filename}
Platform: {self.platform}

Original rule:
{rule_content}

Detection component:
{detect_yaml}

Generate the response component in LimaCharlie D&R YAML format."""

            # Call response generation tool with correct parameter
            print(f"  → Generating response component...")
            respond_result = self.mcp.call_tool("generate_dr_rule_respond", {"query": respond_query})

            # Extract YAML from result - tool returns dict with "respond" or "error" key
            respond_yaml = self._extract_yaml(respond_result)

            if not respond_yaml:
                raise Exception("Response tool returned no YAML content")

            return detect_yaml, respond_yaml, None

        except Exception as e:
            error_msg = str(e)
            # Error will be added to stats by the caller (process_directory)
            return None, None, error_msg

    def _extract_yaml(self, tool_result: Dict) -> Optional[str]:
        """
        Extract YAML content from tool result.

        The MCP tools return a dict with nested structure:
        {
          "content": [...],
          "isError": false,
          "structuredContent": {
            "detection": "yaml string"  // or "respond": "yaml string"
          }
        }

        For large responses (>20KB), the response includes a resource_link:
        {
          "structuredContent": {
            "resource_link": "https://storage.googleapis.com/...",
            "resource_size": 20133,
            "success": true,
            "reason": "results too large, see resource_link for content"
          }
        }

        Args:
            tool_result: Result dictionary from tool call

        Returns:
            YAML string or None
        """
        # Handle different response formats
        if isinstance(tool_result, str):
            return tool_result

        if isinstance(tool_result, dict):
            # Check for error in top level
            if "error" in tool_result:
                raise Exception(f"MCP tool error: {tool_result['error']}")

            # Check for structuredContent first (MCP's actual response format)
            if "structuredContent" in tool_result:
                structured = tool_result["structuredContent"]
                if isinstance(structured, dict):
                    # Check if response is too large and has resource_link
                    if "resource_link" in structured and structured.get("success"):
                        resource_link = structured["resource_link"]
                        print(f"      → Fetching large response from resource link ({structured.get('resource_size', 'unknown')} bytes)...")

                        try:
                            response = requests.get(resource_link, timeout=30)
                            response.raise_for_status()

                            # The response might be JSON containing the YAML, or direct YAML/text
                            content = response.text

                            # Try to parse as JSON first
                            try:
                                json_data = response.json()

                                # Look for detection or respond in the fetched JSON
                                for field in ["detection", "respond"]:
                                    if field in json_data:
                                        value = json_data[field]
                                        if isinstance(value, str):
                                            return value
                                        elif isinstance(value, dict):
                                            return yaml.dump(value, default_flow_style=False)

                                # If the whole JSON response is the YAML structure, convert it
                                if isinstance(json_data, dict):
                                    return yaml.dump(json_data, default_flow_style=False)

                            except json.JSONDecodeError:
                                # Not JSON, might be direct YAML text
                                return content

                        except requests.RequestException as e:
                            raise Exception(f"Failed to fetch resource from link: {e}")

                    # Look for detection or respond in structuredContent
                    for field in ["detection", "respond"]:
                        if field in structured:
                            value = structured[field]
                            if isinstance(value, str):
                                return value
                            elif isinstance(value, dict):
                                return yaml.dump(value, default_flow_style=False)

                    # If structuredContent has error
                    if "error" in structured:
                        raise Exception(f"MCP tool error: {structured['error']}")

            # Fall back to checking top-level fields
            for field in ["detection", "respond", "yaml", "content", "result", "data", "output"]:
                if field in tool_result:
                    value = tool_result[field]
                    if isinstance(value, str):
                        return value
                    elif isinstance(value, dict):
                        # If it's already a dict, convert to YAML
                        return yaml.dump(value, default_flow_style=False)

            # Last resort: convert the whole dict to YAML
            if tool_result:
                return yaml.dump(tool_result, default_flow_style=False)

        return None

    def process_directory(self, input_dir: Path, output_dir: Path, max_workers: int = 20):
        """
        Process all rule files in a directory with parallel execution.

        Args:
            input_dir: Directory containing source rules
            output_dir: Directory to write converted rules
            max_workers: Maximum number of parallel workers (default: 10)
        """
        # Get all files in the directory (excluding hidden files and output dir)
        rule_files = [
            f for f in input_dir.iterdir()
            if f.is_file() and not f.name.startswith('.') and f != output_dir
        ]

        if not rule_files:
            print(f"No rule files found in {input_dir}")
            return

        self.conversion_stats["total"] = len(rule_files)

        print(f"\nProcessing {len(rule_files)} rule file(s) with {max_workers} parallel workers:\n")

        # Create a worker function for processing a single rule
        def process_single_rule(rule_file: Path, total: int) -> Tuple[Path, bool, Optional[str]]:
            """
            Process a single rule file.

            Returns:
                Tuple of (rule_file, success, error_message)
            """
            try:
                # Read rule content
                with open(rule_file, 'r', encoding='utf-8') as f:
                    rule_content = f.read()

                if not rule_content.strip():
                    return (rule_file, False, "Empty file")

                # Convert the rule
                detect_yaml, respond_yaml, error_msg = self.convert_rule(rule_content, rule_file.name)

                if detect_yaml and respond_yaml:
                    # Combine into final D&R rule format
                    combined_rule = self._create_dr_rule(detect_yaml, respond_yaml)

                    # Write to output file (preserve original filename)
                    output_file = output_dir / f"{rule_file.stem}.yaml"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(combined_rule)

                    return (rule_file, True, None)
                else:
                    return (rule_file, False, error_msg or "Conversion failed")

            except Exception as e:
                return (rule_file, False, str(e))

        # Use ThreadPoolExecutor for parallel processing
        completed_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_rule = {
                executor.submit(process_single_rule, rule_file, len(rule_files)): rule_file
                for rule_file in rule_files
            }

            # Process results as they complete
            for future in as_completed(future_to_rule):
                rule_file, success, error = future.result()
                completed_count += 1

                # Thread-safe stats update
                with self.stats_lock:
                    if success:
                        self.conversion_stats["success"] += 1
                        print(f"[{completed_count}/{len(rule_files)}] {rule_file.name} ... ✓ Success")
                    else:
                        self.conversion_stats["failed"] += 1
                        if error:
                            self.conversion_stats["errors"].append({
                                "file": rule_file.name,
                                "error": error
                            })
                        print(f"[{completed_count}/{len(rule_files)}] {rule_file.name} ... ✗ {error if error else 'Failed'}")

    def _create_dr_rule(self, detect_yaml: str, respond_yaml: str) -> str:
        """
        Create the final D&R rule YAML by combining detect and respond sections.

        Args:
            detect_yaml: Detection YAML string
            respond_yaml: Response YAML string

        Returns:
            Combined D&R rule YAML string
        """
        # Parse the YAML strings to ensure valid YAML
        try:
            detect_data = yaml.safe_load(detect_yaml)
            respond_data = yaml.safe_load(respond_yaml)
        except yaml.YAMLError as e:
            # If parsing fails, try to clean up the YAML
            detect_data = detect_yaml
            respond_data = respond_yaml

        # Create the final structure
        dr_rule = {
            "detect": detect_data,
            "respond": respond_data
        }

        # Convert back to YAML with proper formatting
        final_yaml = yaml.dump(dr_rule, default_flow_style=False, sort_keys=False)

        return final_yaml

    def generate_report(self, output_dir: Path, start_time: datetime, end_time: datetime):
        """
        Generate a detailed conversion report.

        Args:
            output_dir: Directory where report will be written
            start_time: Conversion start time
            end_time: Conversion end time
        """
        duration = (end_time - start_time).total_seconds()

        report_lines = [
            "=" * 70,
            "LIMACHARLIE RULE CONVERSION REPORT",
            "=" * 70,
            "",
            f"Generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {duration:.2f} seconds",
            "",
            "SUMMARY",
            "-" * 70,
            f"Total rules processed: {self.conversion_stats['total']}",
            f"Successfully converted: {self.conversion_stats['success']}",
            f"Failed conversions: {self.conversion_stats['failed']}",
            f"Success rate: {(self.conversion_stats['success'] / max(self.conversion_stats['total'], 1)) * 100:.1f}%",
            "",
        ]

        if self.conversion_stats["errors"]:
            report_lines.extend([
                "ERRORS",
                "-" * 70,
            ])

            for error in self.conversion_stats["errors"]:
                report_lines.append(f"\nFile: {error['file']}")
                report_lines.append(f"Error: {error['error']}")

            report_lines.append("")

        report_lines.extend([
            "=" * 70,
            "END OF REPORT",
            "=" * 70,
        ])

        report_content = "\n".join(report_lines)

        # Write report to file
        report_file = output_dir / "report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        # Also print summary to console
        print("\n" + "=" * 50)
        print("Conversion Complete!")
        print("=" * 50)
        print(f"Converted: {self.conversion_stats['success']}/{self.conversion_stats['total']} rules")
        print(f"Failed: {self.conversion_stats['failed']}/{self.conversion_stats['total']} rules")
        print(f"See {report_file} for details")
        print("=" * 50 + "\n")


def get_user_input(prompt: str, default: Optional[str] = None, required: bool = True) -> str:
    """
    Get input from user with optional default value.

    Args:
        prompt: Prompt to display
        default: Default value if user presses Enter
        required: Whether input is required

    Returns:
        User input string
    """
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    while True:
        value = input(full_prompt).strip()

        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print("This field is required. Please enter a value.")


def confirm_data_ingestion(platform: str) -> bool:
    """
    Confirm that the user has set up data ingestion for the platform.

    Args:
        platform: Platform name

    Returns:
        True if confirmed, False otherwise
    """
    print("\n" + "=" * 70)
    print("IMPORTANT: Data Ingestion Verification")
    print("=" * 70)
    print(f"\nThe AI conversion tools require that you have already configured the")
    print(f"'{platform}' platform/adapter in LimaCharlie and that data is actively")
    print(f"being ingested. The tools analyze your actual data schema to generate")
    print(f"accurate detection rules.")
    print("\nHave you:")
    print(f"  1. Set up the '{platform}' adapter/sensor in LimaCharlie?")
    print(f"  2. Verified events are flowing in the Timeline?")
    print(f"  3. Waited at least 5-10 minutes for data collection?")
    print("\n" + "=" * 70)

    while True:
        response = input("\nHave you completed these steps? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            print("\nPlease set up data ingestion first. See the MIGRATION_GUIDE.md")
            print("for detailed instructions on configuring adapters and platforms.")
            return False
        else:
            print("Please answer 'yes' or 'no'")


def main():
    """Main entry point for the conversion script."""

    parser = argparse.ArgumentParser(
        description="Convert security rules to LimaCharlie D&R format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended for first-time users)
  python convert_rules.py

  # Non-interactive mode with command-line arguments
  python convert_rules.py \\
    --oid "YOUR_OID" \\
    --api-key "YOUR_API_KEY" \\
    --platform "okta" \\
    --rules-dir "/path/to/rules" \\
    --parallel-workers 10 \\
    --skip-confirmation
        """
    )

    parser.add_argument("--oid", help="LimaCharlie Organization ID")
    parser.add_argument("--api-key", help="LimaCharlie API Key")
    parser.add_argument("--platform", help="Source platform name (e.g., okta, crowdstrike)")
    parser.add_argument("--rules-dir", help="Directory containing source rules")
    parser.add_argument("--output-dir", help="Output directory (default: rules-dir/output)")
    parser.add_argument("--parallel-workers", type=int, default=10,
                       help="Number of parallel workers for rule conversion (default: 10, min: 1, max: 50)")
    parser.add_argument("--skip-confirmation", action="store_true",
                       help="Skip data ingestion confirmation prompt")
    parser.add_argument("--endpoint", default="https://mcp.limacharlie.io/mcp",
                       help="MCP server endpoint (default: https://mcp.limacharlie.io/mcp)")

    args = parser.parse_args()

    # Validate parallel_workers
    if args.parallel_workers < 1 or args.parallel_workers > 50:
        print(f"ERROR: --parallel-workers must be between 1 and 50 (got {args.parallel_workers})")
        sys.exit(1)

    print("=" * 70)
    print("LIMACHARLIE RULE CONVERSION TOOL")
    print("=" * 70)
    print()

    # Try to auto-detect credentials first (unless explicitly provided via CLI)
    oid = None
    api_key = None
    creds_source = None

    if not args.oid or not args.api_key:
        detected_oid, detected_api_key, detected_source = load_limacharlie_credentials()

        if detected_oid and detected_api_key:
            print(f"✓ Found LimaCharlie credentials from {detected_source}")
            print(f"  Organization ID: {detected_oid}")
            print(f"  API Key: {mask_api_key(detected_api_key)}")
            print()

            # Ask user to confirm
            response = input("Use these credentials? (yes/no) [yes]: ").strip().lower()
            if not response or response in ['yes', 'y']:
                oid = detected_oid
                api_key = detected_api_key
                creds_source = detected_source
                print("✓ Using detected credentials\n")
            else:
                print("Credentials declined. Please enter manually.\n")

    # Get configuration from args or interactive prompts
    if args.oid:
        oid = args.oid
    elif not oid:
        print("First, we need your LimaCharlie credentials.")
        print("You can find these in the LimaCharlie web interface under Access Management > REST API")
        print()
        oid = get_user_input("Enter your LimaCharlie Organization ID (OID)")

    if args.api_key:
        api_key = args.api_key
    elif not api_key:
        api_key = get_user_input("Enter your LimaCharlie API Key")

    if args.platform:
        platform = args.platform
    else:
        print("\nEnter the source platform name. This should match the platform you've")
        print("configured in LimaCharlie (e.g., 'okta', 'crowdstrike', 'windows', 'linux').")
        platform = get_user_input("Enter the source platform name").lower()

    if args.rules_dir:
        rules_dir = Path(args.rules_dir)
    else:
        print("\nEnter the path to the directory containing your source rules.")
        rules_dir_str = get_user_input("Enter the rules directory path", default="./rules")
        rules_dir = Path(rules_dir_str).expanduser().resolve()

    if not rules_dir.exists():
        print(f"\nERROR: Directory not found: {rules_dir}")
        sys.exit(1)

    if not rules_dir.is_dir():
        print(f"\nERROR: Path is not a directory: {rules_dir}")
        sys.exit(1)

    # Confirm data ingestion
    if not args.skip_confirmation:
        if not confirm_data_ingestion(platform):
            print("\nExiting. Please set up data ingestion and try again.")
            sys.exit(1)

    # Set up output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = rules_dir / "output"

    output_dir.mkdir(exist_ok=True)

    print(f"\nProcessing rules from: {rules_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Initialize MCP client
    try:
        mcp_client = MCPClient(api_key, oid, args.endpoint)
    except Exception as e:
        print(f"\nERROR: Failed to initialize MCP client: {e}")
        sys.exit(1)

    # Initialize rule converter
    converter = RuleConverter(mcp_client, platform)

    # Discover tools
    detection_tool, respond_tool = converter.discover_tools()

    if not detection_tool or not respond_tool:
        print("\nERROR: Required tools not found on MCP server.")
        print("Please ensure:")
        print("  1. You have AI features enabled in your LimaCharlie organization")
        print("  2. Your API key has proper permissions")
        print("  3. The MCP server is accessible")
        print("\nContact LimaCharlie support if issues persist.")
        sys.exit(1)

    print()

    # Process all rules
    start_time = datetime.now()

    try:
        converter.process_directory(rules_dir, output_dir, max_workers=args.parallel_workers)
    except KeyboardInterrupt:
        print("\n\nConversion interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Unexpected error during conversion: {e}")
        sys.exit(1)

    end_time = datetime.now()

    # Generate report
    converter.generate_report(output_dir, start_time, end_time)


if __name__ == "__main__":
    main()
