from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)


EXPECTED_INDEXES = {
    "ix_shadow_executions_executed_at": (
        "executed_at",
    ),
    "ix_shadow_executions_status_executed_at": (
        "result_status",
        "executed_at",
    ),
    "ix_shadow_executions_requested_by_executed_at": (
        "requested_by",
        "executed_at",
    ),
    "ix_shadow_executions_model_version_executed_at": (
        "model_version",
        "executed_at",
    ),
    "ix_shadow_executions_order_executed_at": (
        "internal_order_id",
        "executed_at",
    ),
}


def model_indexes() -> dict[str, tuple[str, ...]]:
    return {
        index.name: tuple(
            column.name
            for column in index.columns
        )
        for index in (
            ShadowValuationExecutionModel
            .__table__
            .indexes
        )
        if index.name is not None
    }


def test_model_declares_query_indexes() -> None:
    indexes = model_indexes()

    for index_name, expected_columns in (
        EXPECTED_INDEXES.items()
    ):
        assert index_name in indexes
        assert indexes[index_name] == expected_columns


def test_query_indexes_are_not_unique() -> None:
    indexes = {
        index.name: index
        for index in (
            ShadowValuationExecutionModel
            .__table__
            .indexes
        )
        if index.name in EXPECTED_INDEXES
    }

    assert set(indexes) == set(EXPECTED_INDEXES)

    assert all(
        index.unique is not True
        for index in indexes.values()
    )


def test_order_history_index_starts_with_order_id() -> None:
    indexes = model_indexes()

    columns = indexes[
        "ix_shadow_executions_order_executed_at"
    ]

    assert columns[0] == "internal_order_id"
    assert columns[1] == "executed_at"


def test_filtered_indexes_end_with_execution_time() -> None:
    indexes = model_indexes()

    composite_index_names = {
        "ix_shadow_executions_status_executed_at",
        "ix_shadow_executions_requested_by_executed_at",
        "ix_shadow_executions_model_version_executed_at",
        "ix_shadow_executions_order_executed_at",
    }

    for index_name in composite_index_names:
        assert indexes[index_name][-1] == "executed_at"
