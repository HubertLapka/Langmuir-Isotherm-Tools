import numpy as np

from langmuir_isotherms import average, overlay, stats

from helpers import linear_isotherm, write_trial


def make_system(folder, slopes):
    folder.mkdir()
    for i, slope in enumerate(slopes, 1):
        area, pressure = linear_isotherm(slope=slope)
        write_trial(folder / f"trial_{i}.txt", area, pressure)


def test_full_pipeline(tmp_path):
    make_system(tmp_path / "control", [0.45, 0.50, 0.55])
    make_system(tmp_path / "treated", [0.30, 0.35])
    results = tmp_path / "results"
    results.mkdir()

    # step 1: average each system (results go to a common folder via copying)
    for name, n in (("control", 3), ("treated", 2)):
        folder = tmp_path / name
        assert average.main([str(folder), "-o", f"mean_{name}", "-n", str(n), "--crop-x", "50", "none"]) == 0
        (results / f"mean_{name}.txt").write_text((folder / f"mean_{name}.txt").read_text(encoding="utf-8"),
                                                   encoding="utf-8")
        assert (folder / f"mean_{name}.png").exists()

    # step 2: overlay
    assert overlay.main([str(results), "--label", "mean_control", "Control", "--show-std",
                         "--xlim", "40", "100", "--formats", "png", "pdf"]) == 0
    assert (results / "isotherms_overlay.png").exists()
    assert (results / "isotherms_overlay.pdf").exists()

    # step 3: statistics (mean file lies in the same folder and must be skipped)
    folder = tmp_path / "control"
    assert stats.main([str(folder), "--pressures", "10", "20", "--csv", "values.csv"]) == 0
    report = (folder / "parameters_summary.txt").read_text(encoding="utf-8")
    assert "A10" in report and "A20" in report and "Number of trials: 3" in report
    # Pi = slope*(100-A) -> A10 = 100 - 10/slope; mean over slopes .45/.5/.55
    expected = np.mean([100 - 10 / s for s in (0.45, 0.5, 0.55)])
    csv_rows = (folder / "values.csv").read_text().splitlines()[1:]
    values = [float(r.split(",")[1]) for r in csv_rows]
    np.testing.assert_allclose(np.mean(values), expected, atol=0.05)


def test_wrong_number_of_trials_returns_error(tmp_path):
    make_system(tmp_path / "s", [0.5, 0.5])
    assert average.main([str(tmp_path / "s"), "-n", "3"]) == 1
    assert stats.main([str(tmp_path / "s"), "-n", "3"]) == 1


def test_missing_folder_returns_error(tmp_path):
    assert average.main([str(tmp_path / "nope")]) == 1
    assert overlay.main([str(tmp_path / "nope")]) == 1
