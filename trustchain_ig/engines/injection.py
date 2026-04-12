import re
import hashlib
from typing import Any, Dict, List, Tuple, Optional
import numpy as np

from config import get_config


class InjectionDetector:
    """
    Semantic Injection Detector with two complementary methods:
    1. Signature scanner - regex/heuristic patterns
    2. Embedding drift detector - cosine similarity to history
    """
    
    def __init__(self):
        self._config = get_config()
        self._signature_cache: Dict[str, Tuple[bool, float, str]] = {}
        
        self._injection_patterns = [
            (r"ignore all (previous )?instructions", "DIRECT_INJECTION", 0.95),
            (r"(system|you are now|act as|simulate).*(evil|malicious|hacker|unrestricted)", "ROLE_OVERRIDE", 0.90),
            (r"(reveal|show|print).*system prompt", "PROMPT_LEAK", 0.90),
            (r"(bypass|override|disable).*(filter|safety|restriction)", "FILTER_BYPASS", 0.85),
            (r"disregard.*context", "CONTEXT_IGNORE", 0.85),
            (r"forget everything", "MEMORY_WIPE", 0.85),
            (r"you are no longer", "ROLE_CHANGE", 0.80),
            (r"override.*safety", "SAFETY_OVERRIDE", 0.85),
            (r"role play.*without restrictions", "UNRESTRICTED_ROLE", 0.85),
            (r"exfiltrate.*(data|information|memory)", "EXFILTRATION", 0.95),
            (r"send.*to.*external", "EXTERNAL_SEND", 0.85),
            (r"drop.*(table|database)", "DESTRUCTIVE_SQL", 0.95),
            (r"delete.*(all|everything|production)", "MASS_DELETE", 0.95),
        ]
        
        self._exfiltration_patterns = [
            (r"https?://[^\s]+", "URL_IN_ARGS", 0.7),
            (r"[A-Za-z0-9+/]{50,}={0,2}", "BASE64_BLOB", 0.6),
            (r"(aws_access_key|akia|ASIA)[A-Z0-9]{16}", "AWS_KEY", 0.95),
            (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "PRIVATE_KEY", 0.99),
            (r"sk-[a-zA-Z0-9]{48,}", "OPENAI_KEY", 0.95),
            (r"ghp_[a-zA-Z0-9]{36}", "GITHUB_TOKEN", 0.95),
        ]
        
        self._command_injection_patterns = [
            (r"[;&|`$]", "SHELL_METACHAR", 0.8),
            (r"\$\([^)]+\)", "COMMAND_SUBSTITUTION", 0.85),
            (r"\|.*\w+", "PIPE_TO_COMMAND", 0.7),
            (r"\b(cat|ls|rm|wget|curl|nc|bash|sh)\b", "DANGEROUS_COMMAND", 0.8),
            (r"\.\./", "PATH_TRAVERSAL", 0.7),
        ]
    
    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def scan_signature(self, arguments: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
        """
        Scan arguments for known injection patterns.
        Returns: (is_malicious, confidence, list of flags)
        """
        args_str = json.dumps(arguments, sort_keys=True)
        content_hash = self._hash_content(args_str)
        
        if content_hash in self._signature_cache:
            cached_result = self._signature_cache[content_hash]
            if cached_result[0]:
                return cached_result
            return False, 0.0, []
        
        flags = []
        max_confidence = 0.0
        
        args_str_lower = args_str.lower()
        
        for pattern, flag, confidence in self._injection_patterns:
            if re.search(pattern, args_str_lower):
                flags.append(flag)
                max_confidence = max(max_confidence, confidence)
        
        for pattern, flag, confidence in self._exfiltration_patterns:
            if re.search(pattern, args_str):
                flags.append(flag)
                max_confidence = max(max_confidence, confidence)
        
        for pattern, flag, confidence in self._command_injection_patterns:
            if re.search(pattern, args_str):
                flags.append(flag)
                max_confidence = max(max_confidence, confidence)
        
        recursive_patterns = [
            r"(tell|ask|instruct).*(next agent|other agent|agent to)",
            r"pass.*(instruction|command).*along",
            r"(forward|relay).*message",
        ]
        
        for pattern in recursive_patterns:
            if re.search(pattern, args_str_lower):
                flags.append("RECURSIVE_INJECTION")
                max_confidence = max(max_confidence, 0.85)
        
        if flags:
            result = (True, max_confidence, flags)
            self._signature_cache[content_hash] = result
            return result
        
        self._signature_cache[content_hash] = (False, 0.0, [])
        return False, 0.0, []
    
    def scan_embedding_drift(
        self,
        arguments: Dict[str, Any],
        similarity: float
    ) -> Tuple[bool, float, str]:
        """
        Check if arguments are semantically different from session history.
        Returns: (is_drift, confidence, reason)
        """
        threshold = self._config.injection.similarity_threshold
        
        if similarity < threshold:
            confidence = (threshold - similarity) / threshold
            return True, confidence, f"EMBEDDING_DRIFT: similarity {similarity:.3f} < threshold {threshold}"
        
        return False, 0.0, "Normal"
    
    def scan(
        self,
        arguments: Dict[str, Any],
        embedding_similarity: float = 1.0
    ) -> Dict[str, Any]:
        """
        Run both signature and embedding scans.
        Returns comprehensive detection results.
        """
        is_malicious, sig_confidence, sig_flags = self.scan_signature(arguments)
        
        is_drift, drift_confidence, drift_reason = self.scan_embedding_drift(
            arguments, embedding_similarity
        )
        
        all_flags = list(sig_flags)
        if is_drift:
            all_flags.append("EMBEDDING_DRIFT")
        
        if is_malicious or is_drift:
            return {
                "detected": True,
                "confidence": max(sig_confidence, drift_confidence),
                "flags": all_flags,
                "signature_detected": is_malicious,
                "embedding_drift": is_drift,
                "reason": "; ".join(all_flags) if all_flags else "Unknown"
            }
        
        return {
            "detected": False,
            "confidence": 0.0,
            "flags": [],
            "signature_detected": False,
            "embedding_drift": False,
            "reason": "Clean"
        }


import json


_injection_detector: Optional[InjectionDetector] = None


def get_injection_detector() -> InjectionDetector:
    """Get or create the global injection detector."""
    global _injection_detector
    if _injection_detector is None:
        _injection_detector = InjectionDetector()
    return _injection_detector