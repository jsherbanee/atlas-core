from atlas_core.rules import (
    EngineeringRuleRegistry,
    register_default_engineering_rules,
)


def test_register_default_engineering_rules_includes_all_rule_families():
    registry = EngineeringRuleRegistry()

    register_default_engineering_rules(registry)

    rule_ids = {rule.rule_id for rule in registry.rules()}
    assert "projection_projector_mount" in rule_ids
    assert "audio_speaker_amplifier" in rule_ids
    assert "infrastructure_conduit" in rule_ids
    assert "video_display_mount" in rule_ids
    assert "control_programming" in rule_ids
    assert "lighting_fixture_safety_cable" in rule_ids
    assert "construction_travel_distance" in rule_ids
