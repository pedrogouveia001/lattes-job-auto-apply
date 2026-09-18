# -*- coding: utf-8 -*-
"""
Backward compatibility bridge for lattes_extractor.
Re-exports universal extraction functions from cv_extractor.
"""

from cv_extractor import (
    extract_text_from_pdf,
    parse_universal_resume,
    parse_lattes_text,
    extract_from_file_or_text
)
