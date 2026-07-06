"""Rules and resolution helpers for Atlas Core."""

from atlas_core.rules.audio import (
    DSPProgrammingRule,
    HearingAssistanceRule,
    MicrophonePowerRule,
    PagingRule,
    SpeakerAmplifierRule,
    WirelessAntennaRule,
    register_audio_rules,
)
from atlas_core.rules.engineering_rule import EngineeringRule
from atlas_core.rules.engineering_rule_engine import EngineeringRuleEngine
from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry
from atlas_core.rules.projection import (
    ProjectionCoolingRule,
    ProjectionPowerRule,
    ProjectionStructureRule,
    ProjectorLensRule,
    ProjectorMountRule,
    register_projection_rules,
)
from atlas_core.rules.resolver import Resolution, ResolutionAction, Resolver

__all__ = [
    "EngineeringRule",
    "EngineeringRuleEngine",
    "EngineeringRuleRegistry",
    "SpeakerAmplifierRule",
    "DSPProgrammingRule",
    "WirelessAntennaRule",
    "PagingRule",
    "HearingAssistanceRule",
    "MicrophonePowerRule",
    "register_audio_rules",
    "ProjectorMountRule",
    "ProjectorLensRule",
    "ProjectionPowerRule",
    "ProjectionStructureRule",
    "ProjectionCoolingRule",
    "register_projection_rules",
    "Resolver",
    "Resolution",
    "ResolutionAction",
]
