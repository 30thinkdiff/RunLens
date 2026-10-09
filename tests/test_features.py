"""Known-signal correctness, sampling validity and honest feature exports."""

from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from runlens.features import (
    add_vector_magnitude,
    analyze_spectrum,
    extract_features,
    feature_csv,
    time_domain_features,
)
from runlens.io import prepare_dataset
from runlens.schemas import ImportConfig, SpectralConfig, WindowConfig


def dataset(times, **channels):
    return prepare_dataset(
        pd.DataFrame({"t": times, **channels}),
        ImportConfig("t", tuple(channels)),
        "Synthetic Data",
    )


def test_known_time_domain_statistics():
    result = time_domain_features([1, 2, 3, 4])
    assert result["mean"] == 2.5
    assert result["variance"] == pytest.approx(1.25)
    assert result["std"] == pytest.approx(np.sqrt(1.25))
    assert result["rms"] == pytest.approx(np.sqrt(7.5))
    assert result["min"] == 1 and result["max"] == 4
    assert result["peak_to_peak"] == 3
    assert result["median"] == 2.5
    assert result["iqr"] == 1.5


def test_constant_and_large_finite_values():
    result = time_domain_features([3, 3, 3])
    assert result["rms"] == 3
    assert result["std"] == result["variance"] == result["iqr"] == 0
    with np.errstate(over="raise", invalid="raise"):
        large = time_domain_features([1e308, 1e308])
    assert large["rms"] == large["median"] == 1e308
    assert large["variance"] == 0
    overflow = time_domain_features([-1e308, 1e308])
    assert np.isnan(overflow["variance"])
    assert "variance" in overflow["overflow_features"]


@pytest.mark.parametrize("values", [[], [np.nan, np.inf]])
def test_empty_or_invalid_has_no_fabricated_features(values):
    result = time_domain_features(values)
    assert result["valid_count"] == 0
    assert np.isnan(result["mean"]) and np.isnan(result["rms"])


def test_nan_policies_record_counts():
    values = [1, np.nan, np.inf, 3]
    omitted = time_domain_features(values)
    assert omitted["valid_count"] == 2 and omitted["invalid_count"] == 2
    assert omitted["mean"] == 2
    assert np.isnan(time_domain_features(values, nan_policy="propagate")["mean"])


def test_window_boundaries_and_optional_partial_tail():
    data = dataset(np.arange(5), x=np.arange(5))
    full = extract_features(
        data, WindowConfig(window_size=3, step_size=2, include_spectral=False)
    )
    assert full.table["row_start"].tolist() == [0, 2]
    assert full.table["row_end"].tolist() == [2, 4]
    partial = extract_features(
        data,
        WindowConfig(
            window_size=3, step_size=2, include_partial=True, include_spectral=False
        ),
    )
    assert partial.table["row_start"].tolist() == [0, 2, 4]
    assert partial.table["sample_count"].tolist() == [3, 3, 1]
    assert partial.table["is_complete"].tolist() == [True, True, False]


def test_short_sequence_returns_headers_or_explicit_partial_window():
    data = dataset([0], x=[2])
    assert extract_features(data).table.empty
    result = extract_features(data, WindowConfig(include_partial=True))
    assert result.table.iloc[0]["rms"] == 2
    assert result.table.iloc[0]["spectral_status"] == "too_short"


def test_magnitude_preserves_axes_and_is_stable():
    original = pd.DataFrame(
        {"x": [3.0, 1e200, np.nan], "y": [4.0, 1e200, 1], "z": [0.0, 0, 2]}
    )
    augmented = add_vector_magnitude(original, ("x", "y", "z"), "norm")
    assert augmented["norm"].iloc[0] == 5
    assert augmented["norm"].iloc[1] == pytest.approx(np.sqrt(2) * 1e200)
    assert np.isnan(augmented["norm"].iloc[2])
    assert original.columns.tolist() == ["x", "y", "z"]
    pd.testing.assert_frame_equal(augmented[original.columns], original)


@pytest.mark.parametrize(
    "axes,name",
    [
        (("x", "x", "z"), "norm"),
        (("x", "y"), "norm"),
        (("x", "y", "missing"), "norm"),
        (("x", "y", "z"), "x"),
    ],
)
def test_invalid_magnitude_mapping(axes, name):
    with pytest.raises(ValueError):
        add_vector_magnitude(pd.DataFrame({"x": [1], "y": [2], "z": [3]}), axes, name)


def test_magnitude_is_additional_feature_channel():
    data = dataset([0, 1, 2], x=[3, 3, 3], y=[4, 4, 4], z=[0, 0, 0])
    result = extract_features(
        data,
        WindowConfig(window_size=3, include_spectral=False),
        magnitude_axes=("x", "y", "z"),
    )
    assert result.table["channel"].tolist() == ["x", "y", "z", "vector_magnitude"]
    assert result.table.iloc[-1]["rms"] == 5
    assert data.signals.columns.tolist() == ["x", "y", "z"]


def test_sine_rms_amplitude_frequency_and_welch_integral():
    t = np.arange(1024) / 256
    values = 2 * np.sin(2 * np.pi * 16 * t)
    temporal = time_domain_features(values)
    assert temporal["rms"] == pytest.approx(np.sqrt(2), rel=1e-12)
    assert temporal["std"] == pytest.approx(np.sqrt(2), rel=1e-12)
    spectrum = analyze_spectrum(values, t)
    assert spectrum.features["dominant_frequency_hz"] == pytest.approx(16)
    assert np.max(spectrum.amplitude) == pytest.approx(2)
    assert spectrum.features["psd_integral"] == pytest.approx(2, rel=1e-12)
    assert spectrum.features["spectral_energy"] == pytest.approx(8, rel=1e-12)
    assert spectrum.features["spectral_centroid_hz"] == pytest.approx(16, rel=1e-12)


def test_nyquist_is_not_doubled():
    spectrum = analyze_spectrum(2 * (-1.0) ** np.arange(32), np.arange(32) / 32)
    assert spectrum.amplitude[-1] == pytest.approx(2)
    assert spectrum.features["dominant_frequency_hz"] == 16


def test_odd_length_one_sided_amplitude():
    t = np.arange(101) / 101
    spectrum = analyze_spectrum(2 * np.sin(2 * np.pi * 10 * t), t)
    assert np.max(spectrum.amplitude) == pytest.approx(2)
    assert spectrum.features["dominant_frequency_hz"] == pytest.approx(10)


def test_zero_and_constant_spectra_are_undefined_not_faults():
    spectrum = analyze_spectrum(np.full(128, 3.0), np.arange(128) / 128)
    assert spectrum.features["dominant_frequency_hz"] is None
    assert spectrum.features["spectral_centroid_hz"] is None
    assert spectrum.features["psd_integral"] == 0
    dc = analyze_spectrum(
        np.full(128, 3.0),
        np.arange(128) / 128,
        config=SpectralConfig(remove_mean=False),
    )
    assert dc.amplitude[0] == 3
    assert dc.features["dominant_frequency_hz"] is None
    assert dc.features["psd_integral"] == pytest.approx(9)


@pytest.mark.parametrize(
    "times", [[0, 1, 1, 2], [0, 1, 0.5, 2], [0, 1, 9, 10], [0, np.nan, 2, 3]]
)
def test_invalid_timing_rejected_without_resampling(times):
    with pytest.raises(ValueError):
        analyze_spectrum(np.ones(len(times)), times)


@pytest.mark.parametrize("values", [[], [1], [1, np.nan], [1, np.inf]])
def test_invalid_signal_or_short_spectrum_rejected(values):
    with pytest.raises(ValueError):
        analyze_spectrum(values, np.arange(len(values)))


def test_jitter_tolerance_is_explicit():
    times = [0, 1, 2.001, 3.001]
    with pytest.raises(ValueError):
        analyze_spectrum([1, 2, 3, 4], times)
    accepted = analyze_spectrum(
        [1, 2, 3, 4], times, config=SpectralConfig(sampling_rtol=0.01)
    )
    assert accepted.features["max_relative_jitter"] == pytest.approx(0.001)


def test_time_features_remain_when_window_spectrum_is_rejected():
    data = dataset([0, 1, 9, 10], x=[1, 2, 3, 4])
    row = extract_features(data, WindowConfig(window_size=4)).table.iloc[0]
    assert row["mean"] == 2.5
    assert row["spectral_status"] == "irregular_sampling"
    assert np.isnan(row["dominant_frequency_hz"])


def test_nonfinite_values_are_not_removed_for_fft_even_under_omit_policy():
    data = dataset([0, 1, 2, 3], x=[1, np.nan, 3, 4])
    row = extract_features(data, WindowConfig(window_size=4)).table.iloc[0]
    assert row["valid_count"] == 3
    assert row["spectral_status"] == "invalid_signal"


def test_feature_csv_roundtrip_contains_parameters_and_original_rows():
    result = extract_features(
        dataset([0, 1, 2, 3], x=[1, 2, 3, 4]),
        WindowConfig(window_size=2, step_size=2, include_spectral=False),
    )
    restored = pd.read_csv(BytesIO(feature_csv(result)))
    assert restored["row_start"].tolist() == [0, 2]
    assert restored["mean"].tolist() == [1.5, 3.5]
    assert restored["window_size"].tolist() == [2, 2]
    assert restored["source_name"].tolist() == ["Synthetic Data", "Synthetic Data"]
    assert restored["time_unit"].tolist() == ["s", "s"]


@pytest.mark.parametrize(
    "params",
    [
        {"window_size": 0},
        {"step_size": -1},
        {"window_size": 1.5},
        {"nan_policy": "fill"},
    ],
)
def test_invalid_window_parameters(params):
    with pytest.raises(ValueError):
        WindowConfig(**params)


@pytest.mark.parametrize(
    "params",
    [
        {"sampling_rtol": -1},
        {"sampling_rtol": 0.5},
        {"sampling_rtol": float("nan")},
        {"welch_nperseg": 1},
    ],
)
def test_invalid_spectral_parameters(params):
    with pytest.raises(ValueError):
        SpectralConfig(**params)


def test_feature_capacity_limit_is_checked_before_computation():
    with pytest.raises(ValueError, match="50,000"):
        extract_features(
            dataset(np.arange(50001), x=np.ones(50001)),
            WindowConfig(window_size=1, step_size=1),
        )


def test_expensive_overlapping_windows_are_rejected_before_computation():
    with pytest.raises(ValueError, match="20,000,000"):
        extract_features(
            dataset(np.arange(10000), x=np.ones(10000)),
            WindowConfig(window_size=5000, step_size=1),
        )


@pytest.mark.parametrize("amplitude", [1e200, 1e-200])
def test_unrepresentable_spectral_power_is_rejected(amplitude):
    t = np.arange(64) / 64
    with pytest.raises(ValueError, match="数值"):
        analyze_spectrum(amplitude * np.sin(2 * np.pi * 8 * t), t)
