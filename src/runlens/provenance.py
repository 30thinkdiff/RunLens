"""One portable table fingerprint and explicit mapping for all analysis results."""

import hashlib

from runlens.schemas import Dataset


def dataset_identity(dataset: Dataset) -> dict:
    return dict(
        data_sha256=hashlib.sha256(
            dataset.raw.to_csv(index=False, lineterminator="\n").encode("utf-8")
        ).hexdigest(),
        fingerprint_format="normalized raw-table CSV, UTF-8, LF",
        import_config=dict(
            timestamp_column=dataset.config.timestamp_column,
            channel_columns=list(dataset.config.channel_columns),
            time_unit=dataset.config.time_unit,
        ),
    )
