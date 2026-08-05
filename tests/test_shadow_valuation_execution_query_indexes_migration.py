import ast
from pathlib import Path


MIGRATION_PATH = Path(
    "migrations/versions/"
    "b7e4c2a9d610_otimiza_consultas_execucoes_sombra.py"
)

EXPECTED_INDEXES = {
    "ix_shadow_executions_executed_at": [
        "executed_at",
    ],
    "ix_shadow_executions_status_executed_at": [
        "result_status",
        "executed_at",
    ],
    "ix_shadow_executions_requested_by_executed_at": [
        "requested_by",
        "executed_at",
    ],
    "ix_shadow_executions_model_version_executed_at": [
        "model_version",
        "executed_at",
    ],
    "ix_shadow_executions_order_executed_at": [
        "internal_order_id",
        "executed_at",
    ],
}


def migration_tree() -> ast.Module:
    source = MIGRATION_PATH.read_text(
        encoding="utf-8-sig"
    )

    return ast.parse(
        source,
        filename=str(MIGRATION_PATH),
    )


def function_node(
    tree: ast.Module,
    function_name: str,
) -> ast.FunctionDef:
    for node in tree.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == function_name
        ):
            return node

    raise AssertionError(
        f"Função ausente: {function_name}"
    )


def call_name(call: ast.Call) -> str | None:
    function = call.func

    if isinstance(function, ast.Attribute):
        return function.attr

    return None


def literal_value(node: ast.AST) -> object:
    return ast.literal_eval(node)


def test_migration_revision_chain() -> None:
    namespace: dict[str, object] = {}

    exec(
        compile(
            MIGRATION_PATH.read_text(
                encoding="utf-8-sig"
            ),
            str(MIGRATION_PATH),
            "exec",
        ),
        namespace,
    )

    assert namespace["revision"] == "b7e4c2a9d610"
    assert namespace["down_revision"] == "a3d7e9f1b204"


def test_upgrade_creates_expected_indexes() -> None:
    tree = migration_tree()
    upgrade = function_node(tree, "upgrade")

    created: dict[str, list[str]] = {}

    for node in ast.walk(upgrade):
        if not isinstance(node, ast.Call):
            continue

        if call_name(node) != "create_index":
            continue

        index_name = literal_value(node.args[0])
        columns = literal_value(node.args[2])

        assert isinstance(index_name, str)
        assert isinstance(columns, list)

        created[index_name] = columns

    assert created == EXPECTED_INDEXES


def test_downgrade_drops_all_indexes_in_reverse_order() -> None:
    tree = migration_tree()
    downgrade = function_node(tree, "downgrade")

    dropped = []

    for statement in downgrade.body:
        if not isinstance(statement, ast.Expr):
            continue

        call = statement.value

        if not isinstance(call, ast.Call):
            continue

        if call_name(call) != "drop_index":
            continue

        dropped.append(
            literal_value(call.args[0])
        )

    assert dropped == list(
        reversed(EXPECTED_INDEXES)
    )


def test_indexes_are_non_unique() -> None:
    tree = migration_tree()
    upgrade = function_node(tree, "upgrade")

    create_calls = [
        node
        for node in ast.walk(upgrade)
        if (
            isinstance(node, ast.Call)
            and call_name(node) == "create_index"
        )
    ]

    assert len(create_calls) == len(EXPECTED_INDEXES)

    for call in create_calls:
        keywords = {
            keyword.arg: keyword.value
            for keyword in call.keywords
        }

        assert "unique" in keywords
        assert literal_value(keywords["unique"]) is False
