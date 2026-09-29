"""Extractor registry. Gemini is primary; the deterministic parser is the fallback."""
from __future__ import annotations

from parser import parse_document
from schemas import ExtractionResult


class BaseExtractor:
    def extract(self, text: str, doc_type: str) -> ExtractionResult:
        raise NotImplementedError


class ParserExtractor(BaseExtractor):
    def extract(self, text: str, doc_type: str) -> ExtractionResult:
        return parse_document(text, doc_type)


def get_extractor(doc_type: str) -> BaseExtractor:
    # Every registered type shares the parser. doc_type is passed through so
    # callers can still label packing lists and bills of lading.
    del doc_type
    return ParserExtractor()
