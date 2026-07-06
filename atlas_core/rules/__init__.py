"""Rules and resolution helpers for Atlas Core."""

from atlas_core.rules.engineering_rule import EngineeringRule
from atlas_core.rules.engineering_rule_engine import EngineeringRuleEngine
from atlas_core.rules.engineering_rule_registry import EngineeringRuleRegistry
from atlas_core.rules.audio import (
    DSPProgrammingRule,
    HearingAssistanceRule,
    MicrophonePowerRule,
    PagingRule,
    SpeakerAmplifierRule,
    WirelessAntennaRule,
    register_audio_rules,
)
from atlas_core.rules.construction import (
    CoordinationRule,
    HealthcareSiteRule,
    LoadInRule,
    MobilizationRule,
    PrevailingWageRule,
    SafetyCertificationRule,
    SiteStorageRule,
    TrashAndCleaningRule,
    TravelDistanceRule,
    register_construction_rules,
)
from atlas_core.rules.control import ControlProgrammingRule, register_control_rules
from atlas_core.rules.infrastructure import (
    BackingRule,
    CablePathwayRule,
    ConduitRule,
    GroundingRule,
    RackCoolingRule,
    RackElevationRule,
    RackPowerRule,
    UPSRule,
    register_infrastructure_rules,
)
from atlas_core.rules.lighting import (
    DMXDistributionRule,
    EmergencyLightingCoordinationRule,
    HouseLightingInterfaceRule,
    LightingConsoleNetworkRule,
    LightingFixtureSafetyCableRule,
    LightingPowerRule,
    register_lighting_rules,
)
from atlas_core.rules.projection import (
    ProjectionCoolingRule,
    ProjectionPowerRule,
    ProjectionStructureRule,
    ProjectorLensRule,
    ProjectorMountRule,
    register_projection_rules,
)
from atlas_core.rules.resolver import Resolution, ResolutionAction, Resolver
from atlas_core.rules.video import (
    CameraPowerRule,
    DisplayMountRule,
    PTZConnectivityRule,
    ProjectionScreenSupportRule,
    VideoWallStructureRule,
    register_video_rules,
)


def register_default_engineering_rules(registry: EngineeringRuleRegistry) -> None:
    register_projection_rules(registry)
    register_audio_rules(registry)
    register_infrastructure_rules(registry)
    register_video_rules(registry)
    register_control_rules(registry)
    register_lighting_rules(registry)
    register_construction_rules(registry)


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
    "TravelDistanceRule",
    "MobilizationRule",
    "LoadInRule",
    "SiteStorageRule",
    "TrashAndCleaningRule",
    "HealthcareSiteRule",
    "PrevailingWageRule",
    "SafetyCertificationRule",
    "CoordinationRule",
    "register_construction_rules",
    "ControlProgrammingRule",
    "register_control_rules",
    "ConduitRule",
    "BackingRule",
    "RackCoolingRule",
    "RackPowerRule",
    "RackElevationRule",
    "UPSRule",
    "GroundingRule",
    "CablePathwayRule",
    "register_infrastructure_rules",
    "ProjectorMountRule",
    "ProjectorLensRule",
    "ProjectionPowerRule",
    "ProjectionStructureRule",
    "ProjectionCoolingRule",
    "register_projection_rules",
    "DisplayMountRule",
    "PTZConnectivityRule",
    "CameraPowerRule",
    "VideoWallStructureRule",
    "ProjectionScreenSupportRule",
    "register_video_rules",
    "LightingFixtureSafetyCableRule",
    "LightingConsoleNetworkRule",
    "LightingPowerRule",
    "DMXDistributionRule",
    "HouseLightingInterfaceRule",
    "EmergencyLightingCoordinationRule",
    "register_lighting_rules",
    "register_default_engineering_rules",
    "Resolver",
    "Resolution",
    "ResolutionAction",
]
