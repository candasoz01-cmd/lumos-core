from types import SimpleNamespace


def test_router_handles_help_general_approval_and_exit(capsys):
    from cli.cli_router import run_cli_loop

    inputs = iter(["yardım", "genel onay aç", "çık"])
    today_actions = [[]]
    general_approval = [False]

    ctx = SimpleNamespace(
        base_dir=".",
        state=SimpleNamespace(pending_intent=None),
        ks=SimpleNamespace(is_initialized=lambda: False),
        pl=SimpleNamespace(),
        mode="offline",
        engine=None,
        saved_notes=[[]],
        note_ops_history=[[]],
        last_response_reason=[None],
        last_action=[None],
        last_response_text=[None],
        today_date=[""],
        today_actions=today_actions,
        current_task=[None],
        current_permission_profile=["rapor"],
        task_store=None,
        aliases={},
        general_approval=general_approval,
        record_note_op=lambda label: None,
        record_today_action=lambda action: today_actions[0].append(action),
    )

    mut_ctx = SimpleNamespace(
        base_dir=".",
        task_store=None,
        current_permission_profile=ctx.current_permission_profile,
        general_approval=general_approval,
        current_task=ctx.current_task,
        last_action=ctx.last_action,
        today_date=ctx.today_date,
        today_actions=today_actions,
        last_task_create_fingerprint=[None],
        record_today_action=ctx.record_today_action,
        event_recording_engine=None,
        pending_intent=[None],
        pending_action=[None],
        policy_runtime_mode="offline",
        policy_is_locked=lambda: True,
    )

    router_ctx = SimpleNamespace(
        base_dir=".",
        aliases={},
        ctx=ctx,
        mut_ctx=mut_ctx,
        pending_ref=[None],
        cli_mode=["normal_komut_modu"],
        last_route=[None],
        last_note_undo=[None],
        get_raw_input=lambda: next(inputs),
        watchdog_tick=lambda: None,
        on_lock_menu=lambda args: None,
        on_presence_menu=lambda args: None,
        on_self_test=lambda: None,
        on_alias_menu=lambda args: None,
        observation_engine=None,
        queue_watcher_tick=None,
        mode="offline",
        on_live_brain=None,
    )

    run_cli_loop(router_ctx)

    out = capsys.readouterr().out
    assert "Temel" in out
    assert "Genel onay açık" in out
    assert "OK" in out
    assert general_approval[0] is True
