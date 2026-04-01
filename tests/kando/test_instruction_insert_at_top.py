"""INSERT_AT_TOP → yorum prepend (patch_apply_executor → propose_text_patch öncesi)."""
from task_engine.executors.patch_apply_executor import expand_insert_at_top_body


def test_expand_prepends_comment_block():
    got = expand_insert_at_top_body("INSERT_AT_TOP:# TEST_OK\n", "x = 0\n")
    assert got == "# TEST_OK\nx = 0\n"


def test_expand_multiline_comments():
    block = "INSERT_AT_TOP:\n# a\n# b\n"
    got = expand_insert_at_top_body(block, "z")
    assert got == "# a\n# b\nz"


def test_expand_none_when_not_comment():
    assert expand_insert_at_top_body("INSERT_AT_TOP:foo\n", "x") is None
