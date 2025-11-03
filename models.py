#!/usr/bin/env python3
"""
Data Models for Legal Judgment Database

This module contains all data models and classes used throughout the application.

Author: Anish
Date: November 2025
"""

from dataclasses import dataclass
from typing import Optional, List


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


@dataclass
class ElasticsearchDocument:
    """Data class for Elasticsearch document structure."""
    title: str
    doc_id: str
    year: Optional[int]
    citations: List[str]
    judges: List[str]
    petitioner_advocates: List[str]
    respondant_advocates: List[str]
    case_duration: str
    outcome: str


@dataclass
class NodeMapping:
    """Data class for node mappings."""
    citation_map: dict
    title_to_judgment_map: dict
    judge_map: dict
    petitioner_advocate_map: dict
    respondant_advocate_map: dict
    outcome_map: dict
    case_duration_map: dict
