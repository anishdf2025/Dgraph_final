#!/usr/bin/env python3
"""
RDF Generator for Legal Judgment Database

This module generates RDF files from Excel data containing legal judgments, citations,
judges, advocates, outcomes, and case durations in a format compatible with Dgraph Live Loader.

Features:
- Processes Excel files with judgment data
- Creates RDF triples for judgments, citations, judges, advocates, outcomes, and case durations
- Supports title-based cross-referencing
- Generates simple, sequential node identifiers
- Compatible with Dgraph Live Loader format

Author: Anish
Date: November 2025
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import json
import ast
from dataclasses import dataclass


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rdf_generator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class JudgmentData:
    """Data class to hold judgment information."""
    idx: int
    title: str
    doc_id: str
    year: Optional[int]
    raw_citations: str
    judge_name: str
    petitioner_advocate: str
    respondant_advocate: str
    case_duration: str
    outcome: str
    judgment_node: str


@dataclass
class ProcessingStats:
    """Data class to hold processing statistics."""
    total_judgments: int = 0
    total_judges: int = 0
    total_citations: int = 0
    total_petitioner_advocates: int = 0
    total_respondant_advocates: int = 0
    total_outcomes: int = 0
    total_case_durations: int = 0
    total_triples: int = 0
    title_matches: int = 0
    citation_matches: int = 0
    judge_relationships: int = 0
    petitioner_advocate_relationships: int = 0
    respondant_advocate_relationships: int = 0
    outcome_relationships: int = 0
    case_duration_relationships: int = 0


class RDFGenerator:
    """
    RDF Generator for Legal Judgment Database.
    
    This class processes Excel files containing legal judgment data and generates
    RDF files compatible with Dgraph Live Loader.
    """
    
    def __init__(self, excel_file_path: str, output_file: str = "judgments.rdf"):
        """
        Initialize the RDF Generator.
        
        Args:
            excel_file_path: Path to the Excel file containing judgment data
            output_file: Output RDF file name
        """
        self.excel_file_path = Path(excel_file_path)
        self.output_file = Path(output_file)
        
        # Data storage
        self.rdf_lines: List[str] = []
        self.citation_map: Dict[str, str] = {}
        self.title_to_judgment_map: Dict[str, str] = {}
        self.judge_map: Dict[str, str] = {}
        self.petitioner_advocate_map: Dict[str, str] = {}
        self.respondant_advocate_map: Dict[str, str] = {}
        self.outcome_map: Dict[str, str] = {}
        self.case_duration_map: Dict[str, str] = {}
        self.judgment_data: List[JudgmentData] = []
        
        # Counters
        self.citation_counter = 1
        self.judge_counter = 1
        self.petitioner_advocate_counter = 1
        self.respondant_advocate_counter = 1
        self.outcome_counter = 1
        self.case_duration_counter = 1
        
        # Statistics
        self.stats = ProcessingStats()
        
        # Validate input file
        if not self.excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
    
    def _load_excel_data(self) -> pd.DataFrame:
        """
        Load and validate Excel data.
        
        Returns:
            DataFrame containing the Excel data
            
        Raises:
            Exception: If Excel file cannot be loaded or is empty
        """
        try:
            logger.info(f"📖 Loading Excel file: {self.excel_file_path}")
            df = pd.read_excel(self.excel_file_path)
            
            if df.empty:
                raise ValueError("Excel file is empty")
            
            logger.info(f"✅ Loaded {len(df)} rows from Excel file")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load Excel file: {e}")
            raise
    
    def _sanitize_string(self, value: Any) -> str:
        """
        Sanitize and validate string values.
        
        Args:
            value: Input value to sanitize
            
        Returns:
            Sanitized string
        """
        if pd.isna(value) or value is None:
            return ""
        
        return str(value).strip().replace('"', '\\"')
    
    def _parse_citations(self, raw_citations: str) -> List[str]:
        """
        Parse citations from various formats.
        
        Args:
            raw_citations: Raw citation string from Excel
            
        Returns:
            List of citation strings
        """
        citations = []
        
        if not raw_citations or raw_citations.lower() in ['nan', '[]', '{}', 'null']:
            return citations
        
        try:
            # Case 1: JSON-like format with dict
            if raw_citations.startswith('{') or 'cited_cases' in raw_citations:
                if not raw_citations.startswith('{'):
                    raw_citations = '{' + raw_citations + '}'
                # Clean up the JSON format
                cleaned_citations = raw_citations.replace("'", '"')
                citation_data = json.loads(cleaned_citations)
                citations = citation_data.get("cited_cases", [])
            
            # Case 2: Python-style list with potential escape issues
            elif raw_citations.startswith('['):
                # Handle common escape issues in Excel data
                cleaned_citations = raw_citations
                # Fix common escape character issues
                cleaned_citations = cleaned_citations.replace('\\"', '"')
                cleaned_citations = cleaned_citations.replace('\\n', ' ')
                cleaned_citations = cleaned_citations.replace('\\t', ' ')
                
                try:
                    # Try direct evaluation first
                    citations = ast.literal_eval(cleaned_citations)
                except (ValueError, SyntaxError):
                    # Fallback: manually parse the list using regex
                    import re
                    # Extract content between quotes
                    pattern = r'"([^"]*)"'
                    citations = re.findall(pattern, cleaned_citations)
                    logger.info(f"Used regex fallback to parse {len(citations)} citations")
            
            # Case 3: Simple comma-separated values
            elif ',' in raw_citations and not raw_citations.startswith('['):
                citations = [c.strip().strip('"\'') for c in raw_citations.split(',')]
                
        except Exception as e:
            logger.warning(f"Could not parse citations '{raw_citations[:100]}...': {e}")
            # Last resort: try to extract any quoted text
            try:
                import re
                pattern = r'"([^"]*)"'
                citations = re.findall(pattern, raw_citations)
                if citations:
                    logger.info(f"Extracted {len(citations)} citations using regex fallback")
            except:
                citations = []
        
        # Clean and filter citations
        cleaned_citations = []
        for c in citations:
            if c and c.strip() and c.strip().lower() not in ['nan', 'null', '']:
                cleaned_citations.append(c.strip())
        
        return cleaned_citations
    
    def _parse_judges(self, raw_judges: str) -> List[str]:
        """
        Parse judge names from various formats.
        
        Args:
            raw_judges: Raw judge string from Excel
            
        Returns:
            List of judge names
        """
        judges = []
        
        if not raw_judges or raw_judges.lower() in ['nan', '[]', '{}', 'null']:
            return judges
        
        try:
            # Case 1: Python-style list with potential escape issues
            if raw_judges.startswith('['):
                # Handle common escape issues in Excel data
                cleaned_judges = raw_judges
                # Fix common escape character issues
                cleaned_judges = cleaned_judges.replace('\\"', '"')
                cleaned_judges = cleaned_judges.replace('\\n', ' ')
                cleaned_judges = cleaned_judges.replace('\\t', ' ')
                
                try:
                    # Try direct evaluation first
                    judges = ast.literal_eval(cleaned_judges)
                except (ValueError, SyntaxError):
                    # Fallback: manually parse the list using regex
                    import re
                    # Extract content between quotes
                    pattern = r'"([^"]*)"'
                    judges = re.findall(pattern, cleaned_judges)
                    logger.info(f"Used regex fallback to parse {len(judges)} judges")
            
            # Case 2: Simple comma-separated values
            elif ',' in raw_judges:
                judges = [j.strip().strip('"\'') for j in raw_judges.split(',')]
            
            # Case 3: Single judge name
            else:
                judges = [raw_judges.strip().strip('"\'')]
                
        except Exception as e:
            logger.warning(f"Could not parse judges '{raw_judges[:100]}...': {e}")
            # Last resort: try to extract any quoted text
            try:
                import re
                pattern = r'"([^"]*)"'
                judges = re.findall(pattern, raw_judges)
                if judges:
                    logger.info(f"Extracted {len(judges)} judges using regex fallback")
            except:
                judges = []
        
        # Clean and filter judges
        cleaned_judges = []
        for j in judges:
            if j and j.strip() and j.strip().lower() not in ['nan', 'null', '']:
                cleaned_judges.append(j.strip())
        
        return cleaned_judges
    
    def _parse_advocates(self, raw_advocates: str) -> List[str]:
        """
        Parse advocate names from various formats.
        
        Args:
            raw_advocates: Raw advocate string from Excel
            
        Returns:
            List of advocate names
        """
        advocates = []
        
        if not raw_advocates or raw_advocates.lower() in ['nan', '[]', '{}', 'null']:
            return advocates
        
        try:
            # Case 1: Python-style list with potential escape issues
            if raw_advocates.startswith('['):
                # Handle common escape issues in Excel data
                cleaned_advocates = raw_advocates
                # Fix common escape character issues
                cleaned_advocates = cleaned_advocates.replace('\\"', '"')
                cleaned_advocates = cleaned_advocates.replace('\\n', ' ')
                cleaned_advocates = cleaned_advocates.replace('\\t', ' ')
                
                try:
                    # Try direct evaluation first
                    advocates = ast.literal_eval(cleaned_advocates)
                except (ValueError, SyntaxError):
                    # Fallback: manually parse the list using regex
                    import re
                    # Extract content between quotes
                    pattern = r'"([^"]*)"'
                    advocates = re.findall(pattern, cleaned_advocates)
                    logger.info(f"Used regex fallback to parse {len(advocates)} advocates")
            
            # Case 2: Simple comma-separated values
            elif ',' in raw_advocates:
                advocates = [a.strip().strip('"\'') for a in raw_advocates.split(',')]
            
            # Case 3: Single advocate name
            else:
                advocates = [raw_advocates.strip().strip('"\'')]
                
        except Exception as e:
            logger.warning(f"Could not parse advocates '{raw_advocates[:100]}...': {e}")
            # Last resort: try to extract any quoted text
            try:
                import re
                pattern = r'"([^"]*)"'
                advocates = re.findall(pattern, raw_advocates)
                if advocates:
                    logger.info(f"Extracted {len(advocates)} advocates using regex fallback")
            except:
                advocates = []
        
        # Clean and filter advocates
        cleaned_advocates = []
        for a in advocates:
            if a and a.strip() and a.strip().lower() not in ['nan', 'null', '']:
                cleaned_advocates.append(a.strip())
        
        return cleaned_advocates
    
    def _collect_judgment_data(self, df: pd.DataFrame) -> None:
        """
        First pass: Collect all judgment data and build title mapping.
        
        Args:
            df: DataFrame containing Excel data
        """
        logger.info("🔄 First pass: Collecting judgment data and titles...")
        
        for idx, row in df.iterrows():
            title = self._sanitize_string(row.get('Title', 'Untitled'))
            doc_id = self._sanitize_string(row.get('doc_id', 'unknown'))
            year = row.get('Year') if pd.notna(row.get('Year')) else None
            raw_citations = self._sanitize_string(row.get('Citation', '[]'))
            judge_name = self._sanitize_string(row.get('Judge_name', ''))
            petitioner_advocate = self._sanitize_string(row.get('Petitioner_advocate', ''))
            respondant_advocate = self._sanitize_string(row.get('Respondant_advocate', ''))
            case_duration = self._sanitize_string(row.get('Case Duration', ''))
            outcome = self._sanitize_string(row.get('Outcome', ''))
            
            judgment_node = f"j{idx+1}"
            
            # Create judgment data object
            judgment_data = JudgmentData(
                idx=idx,
                title=title,
                doc_id=doc_id,
                year=year,
                raw_citations=raw_citations,
                judge_name=judge_name,
                petitioner_advocate=petitioner_advocate,
                respondant_advocate=respondant_advocate,
                case_duration=case_duration,
                outcome=outcome,
                judgment_node=judgment_node
            )
            
            self.judgment_data.append(judgment_data)
            
            # Map title to judgment node for cross-referencing
            if title:
                self.title_to_judgment_map[title.lower()] = judgment_node
        
        self.stats.total_judgments = len(self.judgment_data)
        logger.info(f"✅ Collected {self.stats.total_judgments} judgments and their titles")
    
    def _create_judgment_triples(self, judgment: JudgmentData) -> None:
        """
        Create RDF triples for a judgment.
        
        Args:
            judgment: JudgmentData object containing judgment information
        """
        node = judgment.judgment_node
        escaped_title = judgment.title.replace('"', '\\"')
        
        # Basic judgment properties
        self.rdf_lines.extend([
            f'<{node}> <judgment_id> "{node}" .',
            f'<{node}> <title> "{escaped_title}" .',
            f'<{node}> <doc_id> "{judgment.doc_id}" .',
            f'<{node}> <dgraph.type> "Judgment" .'
        ])
        
        # Add year if present
        if judgment.year is not None:
            self.rdf_lines.append(f'<{node}> <year> "{judgment.year}" .')
    
    def _create_judge_relationship(self, judgment: JudgmentData) -> None:
        """
        Create judge node and relationship if judge information exists.
        
        Args:
            judgment: JudgmentData object containing judgment information
        """
        if not judgment.judge_name or judgment.judge_name.lower() == 'nan':
            return
        
        # Parse judge names (could be multiple judges)
        judge_names = self._parse_judges(judgment.judge_name)
        
        for judge_name in judge_names:
            if not judge_name:
                continue
                
            # Check if judge already exists
            if judge_name in self.judge_map:
                judge_node = self.judge_map[judge_name]
            else:
                # Create new judge node
                judge_node = f"judge{self.judge_counter}"
                self.judge_map[judge_name] = judge_node
                self.judge_counter += 1
                
                # Add judge node triples
                escaped_judge_name = judge_name.replace('"', '\\"')
                self.rdf_lines.extend([
                    f'<{judge_node}> <judge_id> "{judge_node}" .',
                    f'<{judge_node}> <name> "{escaped_judge_name}" .',
                    f'<{judge_node}> <dgraph.type> "Judge" .'
                ])
                
                logger.info(f"👨‍⚖️ Created judge node: {judge_node} for '{judge_name}'")
            
            # Link judgment to judge
            self.rdf_lines.append(f'<{judgment.judgment_node}> <judged_by> <{judge_node}> .')
            self.stats.judge_relationships += 1
    
    def _create_petitioner_advocate_relationship(self, judgment: JudgmentData) -> None:
        """
        Create petitioner advocate node and relationship if advocate information exists.
        
        Args:
            judgment: JudgmentData object containing judgment information
        """
        if not judgment.petitioner_advocate or judgment.petitioner_advocate.lower() == 'nan':
            return
        
        # Parse advocate names (could be multiple advocates)
        advocate_names = self._parse_advocates(judgment.petitioner_advocate)
        
        for advocate_name in advocate_names:
            if not advocate_name:
                continue
                
            # Check if advocate already exists
            if advocate_name in self.petitioner_advocate_map:
                advocate_node = self.petitioner_advocate_map[advocate_name]
            else:
                # Create new advocate node
                advocate_node = f"petitioner_advocate{self.petitioner_advocate_counter}"
                self.petitioner_advocate_map[advocate_name] = advocate_node
                self.petitioner_advocate_counter += 1
                
                # Add advocate node triples
                escaped_advocate_name = advocate_name.replace('"', '\\"')
                self.rdf_lines.extend([
                    f'<{advocate_node}> <advocate_id> "{advocate_node}" .',
                    f'<{advocate_node}> <name> "{escaped_advocate_name}" .',
                    f'<{advocate_node}> <advocate_type> "Petitioner" .',
                    f'<{advocate_node}> <dgraph.type> "Advocate" .'
                ])
                
                logger.info(f"👨‍💼 Created petitioner advocate node: {advocate_node} for '{advocate_name}'")
            
            # Link judgment to advocate
            self.rdf_lines.append(f'<{judgment.judgment_node}> <petitioner_represented_by> <{advocate_node}> .')
            self.stats.petitioner_advocate_relationships += 1
    
    def _create_respondant_advocate_relationship(self, judgment: JudgmentData) -> None:
        """
        Create respondant advocate node and relationship if advocate information exists.
        
        Args:
            judgment: JudgmentData object containing judgment information
        """
        if not judgment.respondant_advocate or judgment.respondant_advocate.lower() == 'nan':
            return
        
        # Parse advocate names (could be multiple advocates)
        advocate_names = self._parse_advocates(judgment.respondant_advocate)
        
        for advocate_name in advocate_names:
            if not advocate_name:
                continue
                
            # Check if advocate already exists
            if advocate_name in self.respondant_advocate_map:
                advocate_node = self.respondant_advocate_map[advocate_name]
            else:
                # Create new advocate node
                advocate_node = f"respondant_advocate{self.respondant_advocate_counter}"
                self.respondant_advocate_map[advocate_name] = advocate_node
                self.respondant_advocate_counter += 1
                
                # Add advocate node triples
                escaped_advocate_name = advocate_name.replace('"', '\\"')
                self.rdf_lines.extend([
                    f'<{advocate_node}> <advocate_id> "{advocate_node}" .',
                    f'<{advocate_node}> <name> "{escaped_advocate_name}" .',
                    f'<{advocate_node}> <advocate_type> "Respondant" .',
                    f'<{advocate_node}> <dgraph.type> "Advocate" .'
                ])
                
                logger.info(f"👨‍💼 Created respondant advocate node: {advocate_node} for '{advocate_name}'")
            
            # Link judgment to advocate
            self.rdf_lines.append(f'<{judgment.judgment_node}> <respondant_represented_by> <{advocate_node}> .')
            self.stats.respondant_advocate_relationships += 1
    
    def _create_outcome_relationship(self, judgment: JudgmentData) -> None:
        """
        Create outcome node and relationship if outcome information exists.
        
        Args:
            judgment: JudgmentData object containing judgment information
        """
        if not judgment.outcome or judgment.outcome.lower() == 'nan':
            return
        
        # Check if outcome already exists
        if judgment.outcome in self.outcome_map:
            outcome_node = self.outcome_map[judgment.outcome]
        else:
            # Create new outcome node
            outcome_node = f"outcome{self.outcome_counter}"
            self.outcome_map[judgment.outcome] = outcome_node
            self.outcome_counter += 1
            
            # Add outcome node triples
            escaped_outcome = judgment.outcome.replace('"', '\\"')
            self.rdf_lines.extend([
                f'<{outcome_node}> <outcome_id> "{outcome_node}" .',
                f'<{outcome_node}> <name> "{escaped_outcome}" .',
                f'<{outcome_node}> <dgraph.type> "Outcome" .'
            ])
            
            logger.info(f"⚖️ Created outcome node: {outcome_node} for '{judgment.outcome}'")
        
        # Link judgment to outcome
        self.rdf_lines.append(f'<{judgment.judgment_node}> <has_outcome> <{outcome_node}> .')
        self.stats.outcome_relationships += 1
    
    def _create_case_duration_relationship(self, judgment: JudgmentData) -> None:
        """
        Create case duration node and relationship if case duration information exists.
        
        Args:
            judgment: JudgmentData object containing judgment information
        """
        if not judgment.case_duration or judgment.case_duration.lower() == 'nan':
            return
        
        # Check if case duration already exists
        if judgment.case_duration in self.case_duration_map:
            case_duration_node = self.case_duration_map[judgment.case_duration]
        else:
            # Create new case duration node
            case_duration_node = f"case_duration{self.case_duration_counter}"
            self.case_duration_map[judgment.case_duration] = case_duration_node
            self.case_duration_counter += 1
            
            # Add case duration node triples
            escaped_case_duration = judgment.case_duration.replace('"', '\\"')
            self.rdf_lines.extend([
                f'<{case_duration_node}> <case_duration_id> "{case_duration_node}" .',
                f'<{case_duration_node}> <duration> "{escaped_case_duration}" .',
                f'<{case_duration_node}> <dgraph.type> "CaseDuration" .'
            ])
            
            logger.info(f"📅 Created case duration node: {case_duration_node} for '{judgment.case_duration}'")
        
        # Link judgment to case duration
        self.rdf_lines.append(f'<{judgment.judgment_node}> <has_case_duration> <{case_duration_node}> .')
        self.stats.case_duration_relationships += 1
    
    def _process_citations(self, judgment: JudgmentData) -> Tuple[int, int]:
        """
        Process citations for a judgment and create appropriate relationships.
        
        Args:
            judgment: JudgmentData object containing judgment information
            
        Returns:
            Tuple of (title_matches, citation_matches)
        """
        citations = self._parse_citations(judgment.raw_citations)
        title_matches = 0
        citation_matches = 0
        
        for citation in citations:
            escaped_citation = citation.replace('"', '\\"')
            citation_lower = citation.lower()
            
            # Check if citation matches an existing judgment title
            if citation_lower in self.title_to_judgment_map:
                # Citation matches a judgment title - link to existing judgment
                existing_judgment_node = self.title_to_judgment_map[citation_lower]
                self.rdf_lines.append(
                    f'<{judgment.judgment_node}> <cites> <{existing_judgment_node}> .'
                )
                title_matches += 1
                logger.debug(f"🎯 Title match: '{citation}' → {existing_judgment_node}")
            else:
                # Citation doesn't match any title - handle as regular citation
                if citation in self.citation_map:
                    citation_node = self.citation_map[citation]
                    citation_matches += 1
                else:
                    # Create new citation node
                    citation_node = f"c{self.citation_counter}"
                    self.citation_map[citation] = citation_node
                    self.citation_counter += 1
                    
                    # Add citation node triples
                    self.rdf_lines.extend([
                        f'<{citation_node}> <judgment_id> "{citation_node}" .',
                        f'<{citation_node}> <title> "{escaped_citation}" .',
                        f'<{citation_node}> <dgraph.type> "Judgment" .'
                    ])
                
                # Add citation relationship
                self.rdf_lines.append(f'<{judgment.judgment_node}> <cites> <{citation_node}> .')
        
        return title_matches, citation_matches
    
    def _process_judgments_and_relationships(self) -> None:
        """
        Second pass: Generate RDF triples for judgments, citations, judges, advocates, outcomes, and case durations.
        """
        logger.info("🔄 Second pass: Processing judgments and all relationships...")
        
        for judgment in self.judgment_data:
            logger.info(f"✓ Processing judgment {judgment.idx + 1}: {judgment.title[:50]}...")
            logger.debug(f"  📄 Doc ID: {judgment.doc_id}, Year: {judgment.year}")
            
            # Create judgment triples
            self._create_judgment_triples(judgment)
            
            # Create judge relationship
            self._create_judge_relationship(judgment)
            
            # Create advocate relationships
            self._create_petitioner_advocate_relationship(judgment)
            self._create_respondant_advocate_relationship(judgment)
            
            # Create outcome and case duration relationships
            self._create_outcome_relationship(judgment)
            self._create_case_duration_relationship(judgment)
            
            # Process citations
            title_matches, citation_matches = self._process_citations(judgment)
            
            if title_matches > 0 or citation_matches > 0:
                logger.info(f"  📊 Relationships: {title_matches} title matches, {citation_matches} citation matches")
            
            # Update statistics
            self.stats.title_matches += title_matches
            self.stats.citation_matches += citation_matches
    
    def _calculate_final_stats(self) -> None:
        """Calculate final processing statistics."""
        self.stats.total_judges = self.judge_counter - 1
        self.stats.total_petitioner_advocates = self.petitioner_advocate_counter - 1
        self.stats.total_respondant_advocates = self.respondant_advocate_counter - 1
        self.stats.total_outcomes = self.outcome_counter - 1
        self.stats.total_case_durations = self.case_duration_counter - 1
        self.stats.total_citations = self.citation_counter - 1
        self.stats.total_triples = len(self.rdf_lines)
    
    def _write_rdf_file(self) -> None:
        """
        Write RDF triples to output file.
        
        Raises:
            Exception: If file cannot be written
        """
        try:
            logger.info(f"💾 Writing RDF file: {self.output_file}")
            with open(self.output_file, "w", encoding="utf-8") as f:
                for line in self.rdf_lines:
                    f.write(line + "\n")
            
            logger.info(f"✅ RDF file written successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to write RDF file: {e}")
            raise
    
    def _print_summary(self) -> None:
        """Print processing summary and usage instructions."""
        print("\n" + "=" * 70)
        print(f"✅ RDF file generated successfully in Dgraph Live format!")
        print(f"📁 Output file: {self.output_file}")
        print(f"📊 Total judgments: {self.stats.total_judgments}")
        print(f"👨‍⚖️ Total judges: {self.stats.total_judges}")
        print(f"👨‍💼 Total petitioner advocates: {self.stats.total_petitioner_advocates}")
        print(f"👨‍💼 Total respondant advocates: {self.stats.total_respondant_advocates}")
        print(f"⚖️ Total outcomes: {self.stats.total_outcomes}")
        print(f"📅 Total case durations: {self.stats.total_case_durations}")
        print(f"🔗 Total RDF triples: {self.stats.total_triples}")
        print(f"🎯 Unique citations: {self.stats.total_citations}")
        print(f"🔗 Title-to-judgment matches: {self.stats.title_matches}")
        print(f"🔗 Regular citation matches: {self.stats.citation_matches}")
        print(f"⚖️ Judge-judgment relationships: {self.stats.judge_relationships}")
        print(f"👨‍💼 Petitioner advocate relationships: {self.stats.petitioner_advocate_relationships}")
        print(f"👨‍💼 Respondant advocate relationships: {self.stats.respondant_advocate_relationships}")
        print(f"⚖️ Outcome relationships: {self.stats.outcome_relationships}")
        print(f"📅 Case duration relationships: {self.stats.case_duration_relationships}")
        print("=" * 70)
        print("🎯 Format features:")
        print("   • Simple node names: j1, j2, j3... for judgments")
        print("   • Simple node names: c1, c2, c3... for citations")
        print("   • Simple node names: judge1, judge2, judge3... for judges")
        print("   • Simple node names: petitioner_advocate1, petitioner_advocate2... for petitioner advocates")
        print("   • Simple node names: respondant_advocate1, respondant_advocate2... for respondant advocates")
        print("   • Simple node names: outcome1, outcome2... for outcomes")
        print("   • Simple node names: case_duration1, case_duration2... for case durations")
        print("   • Angle brackets around node names (required by Dgraph Live)")
        print("   • Title-citation cross-referencing for better linkage")
        print("   • Judge nodes linked to judgments via 'judged_by' predicate")
        print("   • Advocate nodes linked to judgments via 'petitioner_represented_by' and 'respondant_represented_by'")
        print("   • Outcome nodes linked to judgments via 'has_outcome' predicate")
        print("   • Case duration nodes linked to judgments via 'has_case_duration' predicate")
        print("✨ No dummy nodes - uses simple sequential identifiers")
        print("=" * 70)
        print("🚀 Ready to upload to Dgraph using:")
        print(f"   dgraph live --files {self.output_file} --schema rdf.schema")
        print("=" * 70)
    
    def generate_rdf(self) -> None:
        """
        Main method to generate RDF file from Excel data.
        
        Raises:
            Exception: If any step in the process fails
        """
        try:
            # Load Excel data
            df = self._load_excel_data()
            
            # Two-pass processing
            self._collect_judgment_data(df)
            self._process_judgments_and_relationships()
            
            # Calculate statistics and write output
            self._calculate_final_stats()
            self._write_rdf_file()
            
            # Print summary
            self._print_summary()
            
            logger.info("🎉 RDF generation completed successfully!")
            
        except Exception as e:
            logger.error(f"💥 RDF generation failed: {e}")
            raise


def main():
    """Main function to run the RDF generator."""
    try:
        # Configuration
        excel_file = "/home/anish/Desktop/Anish/Dgraph_final/excel_2024_2025/FINAL/5_sample/tests.xlsx"
        output_file = "judgments.rdf"
        
        # Generate RDF
        generator = RDFGenerator(excel_file, output_file)
        generator.generate_rdf()
        
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
