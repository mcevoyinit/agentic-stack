#!/usr/bin/env python3
"""
Academic PDF Export Utility
Converts markdown documents to publication-quality PDFs with validation.
"""

import argparse
import subprocess
import sys
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class ValidationError(Exception):
    """Raised when document validation fails."""
    pass


class AcademicValidator:
    """Validates document structure and formatting."""

    def __init__(self, content: str):
        self.content = content
        self.lines = content.split('\n')
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> Tuple[bool, Dict[str, List[str]]]:
        """Run all validations and return results."""
        checks = {
            'structure': self._validate_structure(),
            'cross_refs': self._validate_cross_references(),
            'typography': self._validate_typography(),
            'content': self._validate_content()
        }

        all_passed = all(checks.values())
        return all_passed, {
            'errors': self.errors,
            'warnings': self.warnings
        }

    def _validate_structure(self) -> bool:
        """Check document structure."""
        passed = True

        # Check for title (first heading)
        if not re.search(r'^#\s+', self.content, re.MULTILINE):
            self.errors.append("STRUCTURE: No title (# heading) found")
            passed = False

        # Check for abstract
        if not re.search(r'abstract|summary', self.content, re.IGNORECASE):
            self.warnings.append("STRUCTURE: No abstract section found")

        # Check section numbering
        sections = re.findall(r'^#+\s+(\d+)\.', self.content, re.MULTILINE)
        if sections:
            expected = 1
            for num in sections:
                if int(num) != expected:
                    self.errors.append(f"STRUCTURE: Section numbering gap - expected {expected}, found {num}")
                    passed = False
                expected = int(num) + 1

        # Check for references section
        if not re.search(r'^#+.*references|bibliography', self.content, re.IGNORECASE | re.MULTILINE):
            self.warnings.append("STRUCTURE: No References section found")

        return passed

    def _validate_cross_references(self) -> bool:
        """Check cross-reference integrity."""
        passed = True

        # Find all figure references and definitions
        fig_refs = set(re.findall(r'Figure\s+(\d+)', self.content))
        fig_defs = set(re.findall(r'!\[(?:Figure\s+)?(\d+)[:\s]', self.content))

        # Also check for figure captions in image alt text
        fig_defs.update(re.findall(r'!\[.*?Figure\s+(\d+)', self.content))

        for ref in fig_refs:
            if ref not in fig_defs:
                self.errors.append(f"CROSS-REF: Figure {ref} referenced but not defined")
                passed = False

        # Find all table references and definitions
        table_refs = set(re.findall(r'Table\s+(\d+)', self.content))
        table_defs = set(re.findall(r'\|\s*Table\s+(\d+)', self.content))

        for ref in table_refs:
            if ref not in table_defs:
                self.warnings.append(f"CROSS-REF: Table {ref} referenced but definition not found")

        # Check citation references [N]
        citations = set(re.findall(r'\[(\d+)\]', self.content))
        # Find reference entries
        ref_section = re.search(r'(?:references|bibliography).*$', self.content,
                                re.IGNORECASE | re.DOTALL)
        if ref_section and citations:
            ref_text = ref_section.group()
            ref_entries = set(re.findall(r'^\s*\[(\d+)\]', ref_text, re.MULTILINE))

            for cite in citations:
                if cite not in ref_entries:
                    self.errors.append(f"CROSS-REF: Citation [{cite}] has no reference entry")
                    passed = False

        return passed

    def _validate_typography(self) -> bool:
        """Check typography standards."""
        passed = True

        # Check for double spaces (excluding code blocks)
        in_code_block = False
        for i, line in enumerate(self.lines, 1):
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

            if not in_code_block:
                if '  ' in line and not line.strip().startswith('|'):  # Exclude tables
                    self.warnings.append(f"TYPOGRAPHY: Double space on line {i}")

                if line.rstrip() != line:
                    self.warnings.append(f"TYPOGRAPHY: Trailing whitespace on line {i}")

        # Check code blocks have language specified
        code_blocks = re.findall(r'```(\w*)\n', self.content)
        unnamed = sum(1 for lang in code_blocks if not lang)
        if unnamed > 0:
            self.warnings.append(f"TYPOGRAPHY: {unnamed} code block(s) without language specification")

        return passed

    def _validate_content(self) -> bool:
        """Check content quality indicators."""
        passed = True

        # Check abstract length
        abstract_match = re.search(
            r'#+\s*abstract\s*\n+(.*?)(?=\n#+|\Z)',
            self.content,
            re.IGNORECASE | re.DOTALL
        )
        if abstract_match:
            word_count = len(abstract_match.group(1).split())
            if word_count < 50:
                self.warnings.append(f"CONTENT: Abstract seems short ({word_count} words, recommend 150-300)")
            elif word_count > 400:
                self.warnings.append(f"CONTENT: Abstract may be too long ({word_count} words)")

        # Check for empty sections
        sections = re.split(r'\n#+\s+', self.content)
        for section in sections[1:]:  # Skip content before first heading
            lines = section.split('\n')
            if len(lines) > 0:
                heading = lines[0]
                content = '\n'.join(lines[1:]).strip()
                if not content:
                    self.warnings.append(f"CONTENT: Section '{heading[:30]}...' appears empty")

        return passed

    def get_report(self) -> str:
        """Generate validation report."""
        lines = [
            "=" * 50,
            "VALIDATION REPORT",
            "=" * 50,
            ""
        ]

        if self.errors:
            lines.append("ERRORS (must fix before export):")
            for err in self.errors:
                lines.append(f"  - {err}")
            lines.append("")

        if self.warnings:
            lines.append("WARNINGS (recommended fixes):")
            for warn in self.warnings:
                lines.append(f"  - {warn}")
            lines.append("")

        if not self.errors and not self.warnings:
            lines.append("All checks passed!")

        lines.append("")
        lines.append(f"Status: {'BLOCKED' if self.errors else 'READY FOR EXPORT'}")
        lines.append("=" * 50)

        return '\n'.join(lines)


def check_dependencies() -> Dict[str, bool]:
    """Check for available PDF engines."""
    deps = {}

    # Check pandoc
    try:
        subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
        deps['pandoc'] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        deps['pandoc'] = False

    # Check xelatex
    try:
        subprocess.run(['xelatex', '--version'], capture_output=True, check=True)
        deps['xelatex'] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        deps['xelatex'] = False

    # Check pdflatex
    try:
        subprocess.run(['pdflatex', '--version'], capture_output=True, check=True)
        deps['pdflatex'] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        deps['pdflatex'] = False

    # Check wkhtmltopdf
    try:
        subprocess.run(['wkhtmltopdf', '--version'], capture_output=True, check=True)
        deps['wkhtmltopdf'] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        deps['wkhtmltopdf'] = False

    return deps


def export_pdf(
    input_path: str,
    output_path: str,
    style: str = 'corda',
    validate: bool = True,
    toc: bool = False,
    bib_path: Optional[str] = None
) -> Tuple[bool, str]:
    """Export markdown to PDF."""

    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        return False, f"Input file not found: {input_path}"

    # Read content
    content = input_file.read_text()

    # Validate if requested
    if validate:
        validator = AcademicValidator(content)
        passed, _ = validator.validate_all()
        print(validator.get_report())

        if not passed:
            return False, "Validation failed. Fix errors before export."

    # Check dependencies
    deps = check_dependencies()

    if not deps['pandoc']:
        return False, "pandoc not installed. Install with: brew install pandoc"

    # Build pandoc command
    cmd = ['pandoc', str(input_file), '-o', str(output_file)]

    # Select PDF engine
    if deps['xelatex']:
        cmd.extend(['--pdf-engine=xelatex'])
    elif deps['pdflatex']:
        cmd.extend(['--pdf-engine=pdflatex'])
    elif deps['wkhtmltopdf']:
        cmd.extend(['--pdf-engine=wkhtmltopdf'])
    else:
        return False, "No PDF engine found. Install xelatex, pdflatex, or wkhtmltopdf."

    # Apply style settings
    if style == 'corda':
        # House style: the classic R3 / Corda whitepaper finish.
        # a4paper, 26mm margins, 11pt, Latin Modern serif (xelatex default),
        # numbered sections, a contents page, navy links via the header asset.
        header = Path(__file__).resolve().parent.parent / 'assets' / 'corda-style.tex'
        cmd.extend([
            '-V', 'documentclass=article',
            '-V', 'papersize=a4',
            '-V', 'geometry:margin=26mm',
            '-V', 'fontsize=11pt',
            '--number-sections',
            # Navy navigational furniture (TOC, refs, cites, URLs); body stays
            # black. cordablue is defined in the header asset below.
            '-V', 'colorlinks=true',
            '-V', 'linkcolor=cordablue',
            '-V', 'citecolor=cordablue',
            '-V', 'urlcolor=cordablue',
            '-V', 'toccolor=cordablue',
        ])
        if header.exists():
            cmd.extend(['--include-in-header', str(header)])
        toc = True  # the Corda look always carries a contents page
    elif style == 'academic':
        cmd.extend([
            '-V', 'geometry:margin=1in',
            '-V', 'fontsize=11pt',
            '-V', 'documentclass=article',
            '--number-sections'
        ])
    elif style == 'ieee':
        cmd.extend([
            '-V', 'geometry:margin=0.75in',
            '-V', 'fontsize=10pt',
            '-V', 'documentclass=IEEEtran',
            '--number-sections'
        ])
    elif style == 'apa':
        cmd.extend([
            '-V', 'geometry:margin=1in',
            '-V', 'fontsize=12pt',
            '-V', 'documentclass=article',
            '-V', 'linestretch=2'
        ])

    # Add table of contents if requested
    if toc:
        cmd.append('--toc')

    # Add bibliography if provided
    if bib_path and Path(bib_path).exists():
        cmd.extend(['--bibliography', bib_path, '--citeproc'])

    # Execute conversion
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Verify output was created
        if output_file.exists():
            size = output_file.stat().st_size
            return True, f"PDF exported successfully: {output_path} ({size:,} bytes)"
        else:
            return False, "PDF generation completed but file not found"

    except subprocess.CalledProcessError as e:
        return False, f"PDF generation failed:\n{e.stderr}"


def main():
    parser = argparse.ArgumentParser(
        description='Export markdown to academic PDF with validation'
    )
    parser.add_argument('--input', '-i', required=True, help='Input markdown file')
    parser.add_argument('--output', '-o', required=True, help='Output PDF file')
    parser.add_argument('--style', '-s', default='corda',
                        choices=['corda', 'academic', 'ieee', 'apa', 'chicago'],
                        help='Document style (default: corda — the house Corda whitepaper finish)')
    parser.add_argument('--validate', '-v', action='store_true',
                        help='Validate document before export')
    parser.add_argument('--toc', action='store_true',
                        help='Include table of contents')
    parser.add_argument('--bib', help='Path to bibliography file')
    parser.add_argument('--check-deps', action='store_true',
                        help='Check available dependencies and exit')

    args = parser.parse_args()

    if args.check_deps:
        deps = check_dependencies()
        print("Dependency Status:")
        for dep, available in deps.items():
            status = "OK" if available else "NOT FOUND"
            print(f"  {dep}: {status}")
        sys.exit(0)

    success, message = export_pdf(
        input_path=args.input,
        output_path=args.output,
        style=args.style,
        validate=args.validate,
        toc=args.toc,
        bib_path=args.bib
    )

    print(message)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
