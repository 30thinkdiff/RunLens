"""Exercise real Streamlit uploads, configuration, filters and error paths."""

import json
from pathlib import Path

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
