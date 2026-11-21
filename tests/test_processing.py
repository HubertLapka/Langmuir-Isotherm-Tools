import numpy as np
import pytest

from langmuir_isotherms import (
    Isotherm,
    IsothermFormatError,
    area_at_pressure,
    average_isotherms,
    read_mean_file,
    read_trial,
    summary_stats,
    write_mean_file,
)

from helpers import linear_isotherm, write_trial


def test_read_trial_handles_decimal_comma_and_sorts(tmp_path):
    area, pressure = linear_isotherm()
    path = tmp_path / "a.txt"
    write_trial(path, area, pressure)
    iso = read_trial(path)
    assert np.all(np.diff(iso.area) > 0)
    assert iso.area.min() == pytest.approx(40.0, abs=1e-3)
    assert iso.pressure.max() == pytest.approx(30.0, abs=1e-3)


def test_read_trial_averages_duplicate_areas(tmp_path):
    path = tmp_path / "dup.txt"
    write_trial(path, [100.0, 100.0, 90.0], [1.0, 3.0, 5.0], decimal_comma=False)
    iso = read_trial(path)
    assert len(iso.area) == 2
    assert iso.pressure[iso.area == 100.0][0] == pytest.approx(2.0)


def test_read_trial_missing_header_raises(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_text("no table here\n", encoding="latin-1")
    with pytest.raises(IsothermFormatError):
        read_trial(path)


def test_read_trial_missing_column_raises(tmp_path):
    area, pressure = linear_isotherm()
    path = tmp_path / "a.txt"
    write_trial(path, area, pressure)
    with pytest.raises(IsothermFormatError):
        read_trial(path, pressure_column="P7")


def test_average_of_two_linear_isotherms_is_linear_mean():
    a1, p1 = linear_isotherm(slope=0.4)
    a2, p2 = linear_isotherm(slope=0.6)
    iso1 = Isotherm("1", a1[::-1], p1[::-1])
    iso2 = Isotherm("2", a2[::-1], p2[::-1])
    mean = average_isotherms([iso1, iso2], step=0.5)
    expected = 0.5 * (100.0 - mean.area)
    assert np.allclose(mean.mean, expected, atol=1e-6)
    assert np.all(mean.n_trials == 2)
    # SD of {0.4k, 0.6k} with ddof=1 is 0.1*sqrt(2)*k
    assert np.allclose(mean.std, 0.1 * np.sqrt(2) * (100.0 - mean.area), atol=1e-6)


def test_average_common_range_vs_union():
    a1, p1 = linear_isotherm(a_max=100, a_min=50)
    a2, p2 = linear_isotherm(a_max=90, a_min=40)
    isos = [Isotherm("1", a1[::-1], p1[::-1]), Isotherm("2", a2[::-1], p2[::-1])]
    common = average_isotherms(isos, step=1.0, common_range_only=True)
    union = average_isotherms(isos, step=1.0, common_range_only=False)
    assert (common.area.min(), common.area.max()) == (50.0, 90.0)
    assert (union.area.min(), union.area.max()) == (40.0, 100.0)
    assert union.n_trials[0] == 1 and np.isnan(union.std[0])


def test_average_without_overlap_raises():
    a1, p1 = linear_isotherm(a_max=100, a_min=80)
    a2, p2 = linear_isotherm(a_max=60, a_min=40)
    isos = [Isotherm("1", a1[::-1], p1[::-1]), Isotherm("2", a2[::-1], p2[::-1])]
    with pytest.raises(ValueError):
        average_isotherms(isos)


def test_area_at_pressure_exact_for_linear_data():
    area, pressure = linear_isotherm(slope=0.5)
    iso = Isotherm("x", area[::-1], pressure[::-1])
    # Pi = 0.5 * (100 - A)  ->  Pi = 20  =>  A = 60
    assert area_at_pressure(iso, 20.0) == pytest.approx(60.0, abs=1e-3)


def test_area_at_pressure_nan_outside_recorded_range():
    area, pressure = linear_isotherm(slope=0.5)  # max pressure 30
    iso = Isotherm("x", area[::-1], pressure[::-1])
    assert np.isnan(area_at_pressure(iso, 35.0))


def test_summary_stats():
    mean, sd, n = summary_stats([1.0, 2.0, 3.0, np.nan])
    assert (mean, n) == (2.0, 3)
    assert sd == pytest.approx(1.0)
    assert np.isnan(summary_stats([5.0])[1])
    assert summary_stats([np.nan])[2] == 0


def test_mean_file_roundtrip(tmp_path):
    area = np.array([100.0, 99.9, 99.8])
    mean = np.array([0.1, 0.2, 0.3])
    std = np.array([np.nan, 0.05, 0.06])
    n = np.array([1, 2, 2])
    for decimal_comma in (True, False):
        path = tmp_path / f"m_{decimal_comma}.txt"
        write_mean_file(path, area, mean, std, n, decimal_comma=decimal_comma)
        iso = read_mean_file(path)
        assert np.allclose(iso.area, np.sort(area))
        assert np.allclose(iso.pressure, mean[np.argsort(area)])
        assert np.isnan(iso.std[-1])  # largest area (100.0) had a single trial
