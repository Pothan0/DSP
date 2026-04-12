import uuid
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

class SecurityGuard:
    def __init__(self):
        # Initialize Presidio components
        self.analyzer = AnalyzerEngine(supported_languages=["en"], default_score_threshold=0.4)
        self.anonymizer = AnonymizerEngine()
        self.vault = {}
        
        # Add a custom recognizer for Internal Account Numbers (Format: ACC-XXXX)
        # Higher score (0.85) to prevent false positives with generic numbers
        account_pattern = r"\bACC-\d{4,8}\b"
        # Correctly initialize using the Pattern class
        pattern_obj = Pattern(name="account_pattern", regex=account_pattern, score=0.85)
        
        account_recognizer = PatternRecognizer(
            supported_entity="INTERNAL_ACCOUNT_ID",
            patterns=[pattern_obj]
        )
        self.analyzer.registry.add_recognizer(account_recognizer)

        
        # Expanded list of entities for banking security
        self.entities = [
            "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "US_SSN", 
            "US_DRIVER_LICENSE", "US_BANK_NUMBER", "CREDIT_CARD", 
            "IBAN_CODE", "IP_ADDRESS", "LOCATION", "INTERNAL_ACCOUNT_ID"
        ]
        
    def scrub_pii(self, text: str) -> str:
        """
        Analyzes the text for PII entities and replaces them with vault tokens.
        """
        if not text:
            return text
            
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language='en'
        )
        
        # Reversible Tokenization
        # Sort results descending so replacements don't mess up indices
        results.sort(key=lambda x: x.start, reverse=True)
        
        scrubbed_text = text
        for res in results:
            pii_value = text[res.start:res.end]
            token = f"<{res.entity_type}_{uuid.uuid4().hex[:8]}>"
            self.vault[token] = pii_value
            scrubbed_text = scrubbed_text[:res.start] + token + scrubbed_text[res.end:]
            
        return scrubbed_text
        
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
        "My internal ID is ACC-12345. My credit card is 1234-5678-9012-3456."
    )
    print("Original:", test_text)
    scrubbed = guard.scrub_pii(test_text)
    print("Scrubbed:", scrubbed)
    print("Unmasked:", guard.unmask_pii(scrubbed))

