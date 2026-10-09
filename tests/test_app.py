"""Exercise real Streamlit uploads, configuration, filters and error paths."""

import json
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app():
    path = Path(__file__).resolve().parents[1] / "app.py"
    return AppTest.from_file(str(path), default_timeout=20).run()


def widget(app, kind, label):
    return next(item for item in getattr(app, kind) if item.label == label)


def upload(app, payload, name="test.csv"):
    app.selectbox(key="source").select("上传 CSV").run()
    app.file_uploader(key="upload").set_value((name, payload, "text/csv")).run()
    assert not app.exception
    return app


def test_default_demo_has_quality_evidence(app):
    assert not app.exception
    assert widget(app, "metric", "样本行").value == "2000"
    assert "Synthetic Data" in app.info[0].value
    kinds = set(app.dataframe[-1].value["kind"])
    assert {
        "large_interval",
        "duplicate_timestamp",
        "reverse_timestamp",
        "missing_value",
    } <= kinds


def test_csv_upload_unit_channel_and_time_filter(app):
    payload = (
        b"t,x,y\n1400000000000000000,1,10\n1400000000005000000,2,20\n"
        b"1400000000010000000,3,30\n1400000000015000000,4,40\n"
    )
    upload(app, payload, "euroc-style.csv")
    widget(app, "selectbox", "时间戳单位（请明确指定）").select("ns").run()
    widget(app, "multiselect", "分析通道").set_value(["y"]).run()
    assert widget(app, "metric", "估计采样频率").value == "200 Hz"
    app.segmented_control(key="view").set_value("信号浏览").run()
    assert not app.exception
    plot = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert [trace["name"] for trace in plot["data"]] == ["y"]
    assert plot["data"][0]["x"] == pytest.approx([0, 0.005, 0.01, 0.015])
    app.slider[0].set_value((0.005, 0.01)).run()
    assert not app.exception
    assert app.dataframe[-1].value["y"].tolist() == ["20", "30"]
    assert app.dataframe[-1].value.iloc[:, 0].tolist() == [1, 2]


def test_time_column_can_be_mapped(app):
    upload(app, b"x,t,y\n1,0,4\n2,1000,5\n3,2000,6\n")
    widget(app, "selectbox", "时间戳列").select("t").run()
    widget(app, "selectbox", "时间戳单位（请明确指定）").select("ms").run()
    assert not app.exception
    assert widget(app, "metric", "估计采样频率").value == "1 Hz"
    assert "t" not in widget(app, "multiselect", "分析通道").value


def test_replacing_file_resets_mapping_and_filters(app):
    upload(app, b"t,x\n0,1\n1,2\n")
    app.segmented_control(key="view").set_value("信号浏览").run()
    app.file_uploader(key="upload").set_value(
        ("new.csv", b"clock,z\n10,7\n20,8\n", "text/csv")
    ).run()
    assert not app.exception
    assert widget(app, "selectbox", "时间戳列").value == "clock"
    assert widget(app, "multiselect", "分析通道").value == ["z"]
    assert app.slider[0].value == (0.0, 10.0)


@pytest.mark.parametrize("payload", [b"", b"t,x\n", b"t,x\nbad,1\n", b"t,x\n0,1,2\n"])
def test_input_errors_are_visible_without_crashing(app, payload):
    upload(app, payload)
    assert app.error
    assert not app.exception


def test_empty_channel_selection_is_actionable(app):
    widget(app, "multiselect", "分析通道").set_value([]).run()
    assert not app.exception
    assert "至少一个" in app.warning[0].value


def test_single_sample_and_conflicting_original_column_names(app):
    upload(app, b"t,RunLens relative time (s),RunLens sample row (0-based)\n10,1,2\n")
    app.segmented_control(key="view").set_value("信号浏览").run()
    assert not app.exception
    assert not app.slider
    assert app.dataframe[-1].value.columns.is_unique
    assert len(app.get("plotly_chart")) == 1


def features_view(app):
    app.segmented_control(key="view").set_value("特征分析").run()
    assert not app.exception
    return app


def compute_features(app, window=4, step=4):
    app.number_input(key="window_size").set_value(window)
    app.number_input(key="step_size").set_value(step)
    app.button(key="compute_features").click().run()
    assert not app.exception
    return app.session_state["feature_result"]


def test_feature_form_and_export_match_uploaded_values(app):
    upload(app, b"t,x\n0,1\n1,2\n2,3\n3,4\n4,5\n")
    features_view(app)
    assert len(app.get("plotly_chart")) == 2
    assert "feature_result" not in app.session_state
    result = compute_features(app)
    assert result.table["mean"].tolist() == [2.5]
    exported = pd.read_csv(BytesIO(app.session_state["feature_csv"]))
    assert exported["row_start"].tolist() == [0]
    assert exported["row_end"].tolist() == [3]
    assert exported["window_size"].tolist() == [4]
    assert exported["spectral_status"].tolist() == ["ok"]
    assert app.get("download_button")[-1].proto.label == "下载特征 CSV"
    # Reruns retain the result, while newly submitted options recompute it.
    app.checkbox(key="include_partial").check()
    app.button(key="compute_features").click().run()
    assert not app.exception
    assert app.session_state["feature_result"].table["row_start"].tolist() == [0, 4]


def test_feature_magnitude_preserves_original_channels(app):
    upload(app, b"t,x,y,z\n0,3,4,0\n1,3,4,0\n2,3,4,0\n3,3,4,0\n")
    features_view(app)
    app.checkbox(key="use_magnitude").check()
    result = compute_features(app)
    assert result.table["channel"].tolist() == ["x", "y", "z", "vector_magnitude"]
    assert result.table["mean"].tolist() == [3, 4, 0, 5]
    app.selectbox(key="spectrum_channel").select("vector_magnitude").run()
    assert not app.exception
    assert app.dataframe[-1].value["psd_integral"].iloc[0] == 0


def test_nan_policies_and_spectrum_rejection_are_visible(app):
    upload(app, b"t,x\n0,1\n1,NaN\n2,3\n3,4\n")
    features_view(app)
    result = compute_features(app)
    assert result.table["mean"].iloc[0] == pytest.approx(8 / 3)
    assert result.table["spectral_status"].iloc[0] == "invalid_signal"
    assert not any(chart.key in ("fft", "psd") for chart in app.get("plotly_chart"))
    assert any("invalid_signal" in item.value for item in app.warning)
    app.selectbox(key="nan_policy").select("propagate")
    result = compute_features(app)
    assert np.isnan(result.table["mean"].iloc[0])
    exported = pd.read_csv(BytesIO(app.session_state["feature_csv"]))
    assert exported["nan_policy"].tolist() == ["propagate"]
    assert exported["valid_count"].tolist() == [3]


def test_irregular_time_spectrum_rejected_in_ui(app):
    upload(app, b"t,x\n0,1\n1,2\n3,3\n4,4\n")
    features_view(app)
    result = compute_features(app)
    assert result.table["spectral_status"].iloc[0] == "irregular_sampling"
    assert result.table["mean"].iloc[0] == 2.5
    assert any("irregular_sampling" in item.value for item in app.warning)


def test_short_feature_series_and_file_replacement(app):
    upload(app, b"t,x\n0,2\n")
    features_view(app)
    result = compute_features(app)
    assert result.table.empty
    app.checkbox(key="include_partial").check()
    result = compute_features(app)
    assert result.table["rms"].tolist() == [2]
    assert result.table["spectral_status"].tolist() == ["too_short"]
    app.file_uploader(key="upload").set_value(
        ("new.csv", b"t,z\n0,7\n1,8\n", "text/csv")
    ).run()
    assert not app.exception
    assert "feature_result" not in app.session_state
    assert "feature_csv" not in app.session_state
    assert app.selectbox(key="spectrum_channel").value == "z"


def test_changing_import_config_clears_feature_result(app):
    features_view(app)
    compute_features(app, 256, 128)
    widget(app, "selectbox", "时间戳单位（请明确指定）").select("ms").run()
    assert not app.exception
    assert "feature_result" not in app.session_state


def test_invalid_magnitude_configuration_is_actionable(app):
    features_view(app)
    app.checkbox(key="use_magnitude").check()
    app.text_input(key="magnitude_name").set_value("accel_x")
    app.button(key="compute_features").click().run()
    assert not app.exception
    assert app.error
    assert "已有通道重复" in app.error[0].value
    assert "feature_result" not in app.session_state


def test_reducing_channels_turns_off_unavailable_magnitude(app):
    features_view(app)
    app.checkbox(key="use_magnitude").check()
    compute_features(app, 256, 128)
    widget(app, "multiselect", "分析通道").set_value(["accel_x"]).run()
    assert not app.exception
    assert not app.checkbox(key="use_magnitude").value
    assert app.checkbox(key="use_magnitude").disabled
    result = compute_features(app, 256, 128)
    assert result.table["channel"].unique().tolist() == ["accel_x"]
    assert not app.error
