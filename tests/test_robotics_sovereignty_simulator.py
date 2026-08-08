from __future__ import annotations

from dataclasses import replace

from robotics_sovereignty.simulator import (
    Command,
    Decision,
    RobotState,
    SovereigntyPolicy,
    SovereigntySimulator,
)


def make_simulator() -> SovereigntySimulator:
    return SovereigntySimulator(
        SovereigntyPolicy.from_capabilities(
            {
                "motion.move",
                "motion.stop",
                "sensor.camera.read",
                "sensor.data.export",
                "firmware.update",
            },
            owner_allowlisted_destinations={"local-lab.invalid"},
        )
    )


def test_boots_offline_in_safe_stopped_state() -> None:
    simulator = make_simulator()

    assert simulator.state == RobotState.SAFE_STOPPED
    assert simulator.network_locked_down is True
    assert simulator.verify_audit_chain() is True


def test_network_lockdown_is_explicit_and_audited() -> None:
    simulator = make_simulator()

    result = simulator.enforce_network_lockdown()

    assert result.decision == Decision.ALLOW
    assert result.reason == "persistent_outbound_connections_blocked"
    assert simulator.network_locked_down is True
    assert simulator.audit_records[-1].event == "network_lockdown"


def test_motion_requires_local_activation_and_exact_capability() -> None:
    simulator = make_simulator()
    denied = simulator.submit(Command("move", capability="motion.move"))
    assert denied.decision == Decision.DENY
    assert denied.reason == "local_control_not_ready"

    activated = simulator.activate_local_control(owner_signature_valid=True)
    assert activated.decision == Decision.ALLOW
    mismatch = simulator.submit(Command("move", capability="sensor.camera.read"))
    assert mismatch.reason == "capability_mismatch"

    allowed = simulator.submit(Command("move", capability="motion.move"))
    assert allowed.decision == Decision.ALLOW
    assert simulator.state == RobotState.MOVING


def test_remote_manufacturer_and_unknown_commands_fail_closed() -> None:
    simulator = make_simulator()
    simulator.activate_local_control(owner_signature_valid=True)

    remote = simulator.submit(
        Command("move", source="vendor_cloud", capability="motion.move")
    )
    kill_switch = simulator.submit(Command("vendor_kill_switch"))
    hidden = simulator.submit(Command("hidden_service_command"))
    unknown = simulator.submit(Command("dance_mode"))

    assert remote.reason == "untrusted_or_remote_source"
    assert kill_switch.reason == "manufacturer_control_forbidden"
    assert hidden.reason == "manufacturer_control_forbidden"
    assert unknown.reason == "unknown_action_fail_closed"
    assert simulator.state == RobotState.READY


def test_sensor_egress_requires_signature_approval_and_allowlist() -> None:
    simulator = make_simulator()
    base = Command(
        "export_sensor_data",
        capability="sensor.data.export",
        destination="local-lab.invalid",
    )

    assert simulator.submit(base).reason == "invalid_local_owner_signature"
    assert (
        simulator.submit(replace(base, owner_signature_valid=True)).reason
        == "explicit_owner_approval_required"
    )
    assert (
        simulator.submit(
            replace(
                base,
                owner_signature_valid=True,
                explicit_owner_approval=True,
                destination="vendor-cloud.invalid",
            )
        ).reason
        == "destination_not_allowlisted"
    )
    allowed = simulator.submit(
        replace(
            base,
            owner_signature_valid=True,
            explicit_owner_approval=True,
        )
    )
    assert allowed.decision == Decision.ALLOW


def test_update_requires_local_signature_and_cannot_run_while_moving() -> None:
    simulator = make_simulator()
    update = Command(
        "install_firmware_update",
        capability="firmware.update",
        explicit_owner_approval=True,
    )

    assert simulator.submit(update).reason == "invalid_local_owner_signature"
    allowed = simulator.submit(replace(update, owner_signature_valid=True))
    assert allowed.decision == Decision.ALLOW

    simulator.activate_local_control(owner_signature_valid=True)
    simulator.submit(Command("move", capability="motion.move"))
    moving = simulator.submit(replace(update, owner_signature_valid=True))
    assert moving.reason == "update_forbidden_while_moving"


def test_heartbeat_loss_safe_stops_and_does_not_auto_resume() -> None:
    simulator = make_simulator()
    simulator.activate_local_control(owner_signature_valid=True)
    simulator.submit(Command("move", capability="motion.move"))

    result = simulator.lumos_heartbeat_lost()

    assert result.state == RobotState.SAFE_STOPPED
    assert simulator.state == RobotState.SAFE_STOPPED
    resumed = simulator.submit(Command("move", capability="motion.move"))
    assert resumed.decision == Decision.DENY


def test_physical_emergency_stop_has_priority_and_requires_physical_reset() -> None:
    simulator = make_simulator()
    simulator.activate_local_control(owner_signature_valid=True)
    simulator.submit(Command("move", capability="motion.move"))

    result = simulator.physical_emergency_stop()

    assert result.state == RobotState.EMERGENCY_STOPPED
    activation = simulator.activate_local_control(owner_signature_valid=True)
    stopped = simulator.submit(Command("stop", capability="motion.stop"))
    assert activation.reason == "physical_reset_required"
    assert stopped.reason == "physical_reset_required"


def test_audit_chain_detects_record_tampering() -> None:
    simulator = make_simulator()
    simulator.activate_local_control(owner_signature_valid=True)
    assert simulator.verify_audit_chain() is True

    original = simulator._audit[1]
    simulator._audit[1] = replace(original, reason="tampered")

    assert simulator.verify_audit_chain() is False
