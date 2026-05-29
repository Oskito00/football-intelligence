from pathlib import Path


def test_make_status_runs_football_data_status_command():
    makefile = Path("Makefile").read_text()

    assert "status:" in makefile
    assert "python -m football_intelligence.cli status" in makefile
