import os
from pathlib import Path
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field
import yaml


class ToolConfig(BaseModel):
    """Configuration for a single tool."""
    tier: Literal["low", "medium", "high", "critical"] = "medium"
    max_calls: Optional[int] = None
    requires_hitl: bool = False
    timeout_seconds: int = 30


class TrustScoreConfig(BaseModel):
    """Trust score engine configuration."""
    initial_score: float = 1.0
    decay_threshold: float = 0.4
    termination_threshold: float = 0.2
    clean_call_delta: float = 0.02
    signature_match_delta: float = -0.25
    embedding_drift_delta: float = -0.15
    hitl_reject_delta: float = -0.40
    hitl_approve_delta: float = 0.05
    unauthorized_tool_delta: float = -0.30
    cross_session_pattern_delta: float = -0.20
    decay_rate_per_minute: float = 0.01


class InjectionConfig(BaseModel):
    """Injection detection configuration."""
    embedding_model: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = 0.30
    embedding_window_size: int = 30
    use_llm_judge: bool = False
    llm_judge_model: Optional[str] = None


class MCPUpstreamServer(BaseModel):
    """Configuration for an upstream MCP server."""
    url: str
    name: str
    enabled: bool = True
    timeout: int = 30


class MCPConfig(BaseModel):
    """MCP server configuration."""
    host: str = "0.0.0.0"
    port: int = 7070
    upstream_servers: List[MCPUpstreamServer] = []
    transport: Literal["stdio", "streamable-http"] = "streamable-http"


class HITLConfig(BaseModel):
    """Human-in-the-loop configuration."""
    enabled: bool = True
    timeout_seconds: int = 300
    timeout_policy: Literal["auto_reject", "auto_approve"] = "auto_reject"


class TelemetryConfig(BaseModel):
    """Observability configuration."""
    log_level: str = "INFO"
    otel_enabled: bool = False
    otel_endpoint: Optional[str] = None
    prometheus_enabled: bool = True
    prometheus_port: int = 9090


class AuditConfig(BaseModel):
    """Audit store configuration."""
    backend: Literal["sqlite", "postgresql"] = "sqlite"
    database_url: str = "trustchain_audit.db"
    retention_days: int = 90


class TrustChainConfig(BaseModel):
    """Main TrustChain configuration."""
    tools: Dict[str, ToolConfig] = {}
    trust: TrustScoreConfig = Field(default_factory=TrustScoreConfig)
    injection: InjectionConfig = Field(default_factory=InjectionConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    hitl: HITLConfig = Field(default_factory=HITLConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)


def load_config(config_path: Optional[str] = None) -> TrustChainConfig:
    """Load configuration from YAML file with environment overrides."""
    
    config_dir = Path(__file__).parent
    default_config_path = config_dir / "defaults.yaml"
    
    config_data = {}
    
    if default_config_path.exists():
        with open(default_config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}
    
    if config_path and Path(config_path).exists():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
            config_data.update(user_config)
    
    env_overrides = {}
    
    def get_env(prefix: str, data: dict, prefix_key: str = ""):
        for key, value in data.items():
            full_key = f"{prefix_key}{key.upper()}" if prefix_key else key.upper()
            env_val = os.environ.get(f"TRUSTCHAIN_{full_key}")
            if env_val is not None:
                if key == "tools":
                    for tool_name, tool_config in value.items():
                        tool_env = os.environ.get(f"TRUSTCHAIN_TOOLS__{tool_name.upper()}__{'TIER'.upper()}")
                        if tool_env:
                            if key not in env_overrides:
                                env_overrides[key] = {}
                            if tool_name not in env_overrides[key]:
                                env_overrides[key][tool_name] = {}
                            env_overrides[key][tool_name]["tier"] = tool_env
                else:
                    if isinstance(value, bool):
                        env_overrides[key] = env_val.lower() in ("true", "1", "yes")
                    elif isinstance(value, int):
                        try:
                            env_overrides[key] = int(env_val)
                        except ValueError:
                            pass
                    elif isinstance(value, float):
                        try:
                            env_overrides[key] = float(env_val)
                        except ValueError:
                            pass
                    else:
                        env_overrides[key] = env_val
    
    def process_nested(data: dict, prefix: str = ""):
        for key, value in data.items():
            if isinstance(value, dict):
                new_prefix = f"{prefix}{key}_" if prefix else f"{key}_"
                process_nested(value, new_prefix)
            else:
                get_env(prefix, {key: value}, prefix)
    
    process_nested(config_data)
    
    for key, value in env_overrides.items():
        if key in config_data and isinstance(config_data[key], dict) and isinstance(value, dict):
            for k, v in value.items():
                if k in config_data[key]:
                    if isinstance(config_data[key][k], dict):
                        config_data[key][k].update(v)
                    else:
                        config_data[key][k] = v
        else:
            config_data[key] = value
    
    return TrustChainConfig(**config_data)


_config: Optional[TrustChainConfig] = None


def get_config() -> TrustChainConfig:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None) -> TrustChainConfig:
    """Reload configuration from file."""
    global _config
    _config = load_config(config_path)
    return _config