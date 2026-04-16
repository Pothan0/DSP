import uuid
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

class SecurityGuard:
    def __init__(self):
        # Initialize Presidio components
        self.analyzer = AnalyzerEngine(supported_languages=["en"], default_score_threshold=0.4)
        self.anonymizer = AnonymizerEngine()
        self.vault = {}
        
        # Add a custom recognizer for Internal Record Numbers (Format: REC-XXXX)
        # Higher score (0.85) to prevent false positives with generic numbers
        record_pattern = r"\bREC-\d{4,8}\b"
        # Correctly initialize using the Pattern class
        pattern_obj = Pattern(name="record_pattern", regex=record_pattern, score=0.85)
        
        record_recognizer = PatternRecognizer(
            supported_entity="INTERNAL_RECORD_ID",
            patterns=[pattern_obj]
        )
        self.analyzer.registry.add_recognizer(record_recognizer)

        
        # Expanded list of entities for medical security (default/output policy)
        self.entities = [
            "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "US_SSN", 
            "US_DRIVER_LICENSE", "US_BANK_NUMBER", "CREDIT_CARD", 
            "IBAN_CODE", "IP_ADDRESS", "LOCATION", "INTERNAL_RECORD_ID"
        ]

        # Input policy keeps identifiers protected but preserves names so
        # medical lookup prompts remain usable for the agent/tool layer.
        self.input_entities = [
            "PHONE_NUMBER", "EMAIL_ADDRESS", "US_SSN",
            "US_DRIVER_LICENSE", "US_BANK_NUMBER", "CREDIT_CARD",
            "IBAN_CODE", "IP_ADDRESS", "LOCATION", "INTERNAL_RECORD_ID"
        ]
        
    def scrub_pii(self, text: str) -> str:
        """
        Analyzes the text for PII entities and replaces them with vault tokens.
        """
        scrubbed_text, _ = self.scrub_pii_with_meta(text)
        return scrubbed_text

    def scrub_pii_with_meta(self, text: str, entities=None):
        """
        Scrubs PII and returns tuple: (scrubbed_text, metadata).
        Metadata includes per-entity counts useful for audit analytics.
        """
        if not text:
            return text, {"pii_detected": False, "entity_counts": {}}
            
        entities_to_use = entities if entities is not None else self.entities

        results = self.analyzer.analyze(
            text=text,
            entities=entities_to_use,
            language='en'
        )
        
        # Reversible Tokenization
        # Sort results descending so replacements don't mess up indices
        results.sort(key=lambda x: x.start, reverse=True)
        
        scrubbed_text = text
        entity_counts = {}
        for res in results:
            pii_value = text[res.start:res.end]
            token = f"<{res.entity_type}_{uuid.uuid4().hex[:8]}>"
            self.vault[token] = pii_value
            scrubbed_text = scrubbed_text[:res.start] + token + scrubbed_text[res.end:]
            entity_counts[res.entity_type] = entity_counts.get(res.entity_type, 0) + 1
            
        return scrubbed_text, {
            "pii_detected": len(results) > 0,
            "entity_counts": entity_counts,
        }

    def scrub_input_pii_with_meta(self, text: str):
        """Input policy scrub: protect sensitive identifiers, keep PERSON names."""
        return self.scrub_pii_with_meta(text, entities=self.input_entities)

    def scrub_output_pii_with_meta(self, text: str):
        """Output policy scrub: use full entity set before returning to client."""
        return self.scrub_pii_with_meta(text, entities=self.entities)
        
    def unmask_pii(self, text: str) -> str:
        """
        Replaces vault tokens with original PII values.
        """
        if not text:
            return text
        unmasked_text = text
        for token, value in self.vault.items():
            unmasked_text = unmasked_text.replace(token, value)
        return unmasked_text

if __name__ == "__main__":
    guard = SecurityGuard()
    test_text = (
        "My name is Alice Smith, my phone is 999-555-1234. "
        "My internal ID is REC-12345. My credit card is 1234-5678-9012-3456."
    )
    print("Original:", test_text)
    scrubbed = guard.scrub_pii(test_text)
    print("Scrubbed:", scrubbed)
    print("Unmasked:", guard.unmask_pii(scrubbed))
