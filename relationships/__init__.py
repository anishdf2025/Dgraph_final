#!/usr/bin/env python3
"""
Relationships Package for Legal Judgment Database

This package contains modular relationship handlers for different types of 
legal judgment relationships including judges, advocates, outcomes, case durations, and citations.

Each handler can be used independently for debugging or as part of the main RDF generator.

Author: Anish
Date: November 2025
"""

from .judge_relationship import JudgeRelationshipHandler
from .advocate_relationship import AdvocateRelationshipHandler
from .outcome_relationship import OutcomeRelationshipHandler
from .case_duration_relationship import CaseDurationRelationshipHandler
from .citation_relationship import CitationRelationshipHandler

__all__ = [
    'JudgeRelationshipHandler',
    'AdvocateRelationshipHandler', 
    'OutcomeRelationshipHandler',
    'CaseDurationRelationshipHandler',
    'CitationRelationshipHandler'
]
