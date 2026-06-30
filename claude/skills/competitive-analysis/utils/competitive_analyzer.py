#!/usr/bin/env python3
"""
Competitive Analysis Orchestrator

Coordinates multi-phase competitive analysis:
1. Intelligence gathering (Slack, web, internal docs)
2. Multi-model analysis (council + kamikaze)
3. Raise integration (optional)
4. Report generation (markdown + PDF)

Usage:
    python3 competitive_analyzer.py --topic "AI Advertising" --company "YourCompany" --include-raise
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Paths
SKILLS_DIR = Path.home() / ".claude" / "skills"
COUNCIL_SCRIPT = SKILLS_DIR / "council" / "utils" / "council_query.py"
KAMIKAZE_SCRIPT = SKILLS_DIR / "kamikaze" / "utils" / "kamikaze_orchestrator_v4.py"
RAISE_DIR = Path.home() / "yourco" / "raise"
OUTPUT_DIR = Path.home() / "yourco" / "docs"


def gather_slack_intel(channel_id: str = "C0XXXXXXXXX", limit: int = 20) -> str:
    """
    Gather intelligence from Slack channel.
    Note: This is a placeholder - actual implementation would use Slack MCP.
    """
    print(f"[INFO] Gathering Slack intel from channel {channel_id}...")
    # In practice, this would be called via MCP
    return "[Slack intel would be gathered here via MCP]"


def web_research(competitors: list[str]) -> dict:
    """
    Research competitors via web search.
    Note: This is a placeholder - actual implementation would use web search tools.
    """
    print(f"[INFO] Researching competitors: {', '.join(competitors)}...")
    results = {}
    for competitor in competitors:
        results[competitor] = f"[Web research for {competitor} would be gathered here]"
    return results


def run_council(prompt: str, context: str) -> dict:
    """Run AI Council for multi-model analysis."""
    print("[INFO] Running AI Council...")

    if not COUNCIL_SCRIPT.exists():
        print(f"[WARN] Council script not found at {COUNCIL_SCRIPT}")
        return {"error": "Council script not found"}

    try:
        result = subprocess.run(
            [sys.executable, str(COUNCIL_SCRIPT), prompt, context, "--full-council", "--json"],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}


def run_kamikaze(topic: str, template: str = "strategy", depth: str = "standard", output_dir: Path = None) -> dict:
    """Run Kamikaze strategic deliberation."""
    print(f"[INFO] Running Kamikaze ({template} template, {depth} depth)...")

    if not KAMIKAZE_SCRIPT.exists():
        print(f"[WARN] Kamikaze script not found at {KAMIKAZE_SCRIPT}")
        return {"error": "Kamikaze script not found"}

    output_dir = output_dir or OUTPUT_DIR / "kamikaze"

    try:
        result = subprocess.run(
            [
                sys.executable, str(KAMIKAZE_SCRIPT),
                "--topic", topic,
                "--template", template,
                "--depth", depth,
                "--output-dir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=1800  # 30 min timeout
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "output_dir": str(output_dir)
        }
    except Exception as e:
        return {"error": str(e)}


def load_raise_docs() -> dict:
    """Load fundraising strategy documents."""
    print("[INFO] Loading raise strategy documents...")

    docs = {}
    key_files = [
        "fundraising_30_60_day_roadmap.md",
        "MA_POSITIONING_GUIDE.md",
        "INVESTOR_MESSAGING_GUIDE.md",
    ]

    for rel_path in key_files:
        full_path = RAISE_DIR / rel_path
        if full_path.exists():
            try:
                docs[rel_path] = full_path.read_text()
                print(f"  - Loaded {rel_path}")
            except Exception as e:
                docs[rel_path] = f"[Error loading: {e}]"
        else:
            docs[rel_path] = "[File not found]"

    return docs


def generate_report(
    topic: str,
    company: str,
    intel: dict,
    council_result: dict,
    kamikaze_result: dict,
    raise_docs: dict = None,
    output_dir: Path = None
) -> Path:
    """Generate markdown report."""
    print("[INFO] Generating report...")

    output_dir = output_dir or OUTPUT_DIR
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"competitive-analysis-{topic.lower().replace(' ', '-')}-{timestamp}.md"
    output_path = output_dir / filename

    # Build report sections
    report = f"""# {topic} Competitive Landscape
## Strategic Assessment & Positioning

**CONFIDENTIAL // PRE-SEED STRATEGY**

---

**DATE:** {datetime.now().strftime('%B %d, %Y')}
**FROM:** Strategic Analysis (AI Council + Kamikaze Deliberation)
**SUBJECT:** {company} Competitive Position Assessment

*This document synthesizes multi-model AI deliberation with adversarial analysis.*

---

## Executive Summary

[Analysis summary will be populated from council/kamikaze results]

---

## 1. Market Intelligence

### Slack Channel Intel
{intel.get('slack', '[No Slack intel gathered]')}

### Web Research
{json.dumps(intel.get('web', {}), indent=2)}

---

## 2. AI Council Analysis

{json.dumps(council_result, indent=2) if council_result else '[Council analysis pending]'}

---

## 3. Kamikaze Strategic Deliberation

Output directory: {kamikaze_result.get('output_dir', 'N/A')}

{kamikaze_result.get('output', '[Kamikaze analysis pending]') if kamikaze_result else '[Kamikaze analysis pending]'}

---
"""

    if raise_docs:
        report += """
## 4. Fundraising Strategy Integration

### Three-Phase Raise Structure
[Extracted from fundraising docs]

### Target Acquirer Matrix
[Extracted from M&A positioning guide]

### Investor Tiering
[Extracted from messaging guide]

---
"""

    report += f"""
---

*Document generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}*
*Analysis method: Competitive Analysis Skill v1.0.0*
"""

    output_path.write_text(report)
    print(f"[INFO] Report saved to: {output_path}")

    return output_path


def convert_to_pdf(markdown_path: Path) -> Path:
    """Convert markdown to PDF using pandoc."""
    print("[INFO] Converting to PDF...")

    pdf_path = markdown_path.with_suffix('.pdf')

    try:
        result = subprocess.run(
            [
                "pandoc", str(markdown_path),
                "-o", str(pdf_path),
                "--pdf-engine=xelatex",
                "-V", "geometry:margin=1in",
                "-V", "fontsize=11pt"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print(f"[INFO] PDF saved to: {pdf_path}")
            return pdf_path
        else:
            print(f"[WARN] PDF conversion failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"[WARN] PDF conversion error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Competitive Analysis Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --topic "AI Advertising" --company "YourCompany" --include-raise
  %(prog)s --topic "Enterprise SaaS" --mode quick
  %(prog)s --topic "FinTech" --depth exhaustive --output ~/reports/
        """
    )

    parser.add_argument("--topic", required=True, help="Market/industry to analyze")
    parser.add_argument("--company", default="", help="Your company for positioning")
    parser.add_argument("--competitors", default="", help="Comma-separated competitor list")
    parser.add_argument("--include-raise", action="store_true", help="Include fundraising strategy sections")
    parser.add_argument("--mode", choices=["quick", "standard", "exhaustive"], default="standard",
                        help="Analysis depth mode")
    parser.add_argument("--depth", choices=["quick", "standard", "thorough", "exhaustive"], default=None,
                        help="Kamikaze depth (overrides --mode for kamikaze)")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--skip-council", action="store_true", help="Skip AI Council")
    parser.add_argument("--skip-kamikaze", action="store_true", help="Skip Kamikaze deliberation")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of report")

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine depth
    depth = args.depth or args.mode

    # Parse competitors
    competitors = [c.strip() for c in args.competitors.split(",")] if args.competitors else []

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         COMPETITIVE ANALYSIS ORCHESTRATOR v1.0.0             ║
╠══════════════════════════════════════════════════════════════╣
║  Topic: {args.topic:<50} ║
║  Company: {args.company or 'N/A':<48} ║
║  Mode: {args.mode:<51} ║
║  Include Raise: {str(args.include_raise):<42} ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Phase 1: Intelligence Gathering
    print("\n" + "="*60)
    print("PHASE 1: INTELLIGENCE GATHERING")
    print("="*60)

    intel = {
        "slack": gather_slack_intel(),
        "web": web_research(competitors or ["Competitor1", "Competitor2"])
    }

    # Phase 2: Multi-Model Analysis
    print("\n" + "="*60)
    print("PHASE 2: MULTI-MODEL ANALYSIS")
    print("="*60)

    council_result = None
    if not args.skip_council:
        council_prompt = f"Analyze {args.company}'s competitive position in {args.topic}"
        council_context = f"Competitors: {', '.join(competitors)}" if competitors else ""
        council_result = run_council(council_prompt, council_context)

    kamikaze_result = None
    if not args.skip_kamikaze and args.mode != "quick":
        kamikaze_topic = f"{args.company} competitive analysis in {args.topic}"
        kamikaze_result = run_kamikaze(
            topic=kamikaze_topic,
            template="strategy",
            depth=depth,
            output_dir=output_dir / "kamikaze"
        )

    # Phase 3: Raise Integration
    raise_docs = None
    if args.include_raise:
        print("\n" + "="*60)
        print("PHASE 3: RAISE INTEGRATION")
        print("="*60)
        raise_docs = load_raise_docs()

    # Phase 4: Report Generation
    print("\n" + "="*60)
    print("PHASE 4: REPORT GENERATION")
    print("="*60)

    if args.json:
        result = {
            "topic": args.topic,
            "company": args.company,
            "intel": intel,
            "council": council_result,
            "kamikaze": kamikaze_result,
            "raise_docs": list(raise_docs.keys()) if raise_docs else None
        }
        print(json.dumps(result, indent=2))
    else:
        report_path = generate_report(
            topic=args.topic,
            company=args.company,
            intel=intel,
            council_result=council_result,
            kamikaze_result=kamikaze_result,
            raise_docs=raise_docs,
            output_dir=output_dir
        )

        pdf_path = convert_to_pdf(report_path)

        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print(f"  Markdown: {report_path}")
        print(f"  PDF: {pdf_path or 'Conversion failed'}")
        if kamikaze_result and kamikaze_result.get('output_dir'):
            print(f"  Kamikaze: {kamikaze_result['output_dir']}")


if __name__ == "__main__":
    main()
