"""High score persistence, including the ways a score file can go wrong.

Every test writes to a `tmp_path`, never the real file in the user's home
directory — a test suite that clobbers someone's scores would be a poor
advertisement for the game.
"""

import json

from tetris.core.highscores import (
    MAX_ENTRIES_PER_MODE,
    HighScore,
    load_scores,
    record_score,
    save_scores,
)


def test_a_missing_file_reads_as_no_scores(tmp_path):
    assert load_scores(tmp_path / "nothing.json") == {}


def test_scores_survive_a_save_and_load(tmp_path):
    path = tmp_path / "scores.json"
    original = {"modern": [HighScore(score=100, lines=4, level=1)]}
    assert save_scores(original, path)
    assert load_scores(path) == original


def test_a_corrupt_file_reads_as_no_scores(tmp_path):
    """Hand-edited, half-written, or simply not JSON — none of it should
    stop someone from playing."""
    path = tmp_path / "scores.json"
    path.write_text("{not json at all", encoding="utf-8")
    assert load_scores(path) == {}


def test_a_file_from_another_version_reads_as_no_scores(tmp_path):
    """Valid JSON, wrong shape: the fields do not match what HighScore
    expects, and the loader must not raise on it."""
    path = tmp_path / "scores.json"
    path.write_text(json.dumps({"modern": [{"points": 10}]}), encoding="utf-8")
    assert load_scores(path) == {}


def test_scores_are_ranked_highest_first(tmp_path):
    path = tmp_path / "scores.json"
    record_score("modern", HighScore(score=100, lines=1, level=1), path)
    record_score("modern", HighScore(score=500, lines=8, level=2), path)
    table, _ = record_score("modern", HighScore(score=300, lines=4, level=1), path)
    assert [entry.score for entry in table] == [500, 300, 100]


def test_only_the_top_scores_are_kept(tmp_path):
    path = tmp_path / "scores.json"
    table: list[HighScore] = []
    for score in range(1, MAX_ENTRIES_PER_MODE + 5):
        table, _ = record_score("modern", HighScore(score * 10, 1, 1), path)
    assert len(table) == MAX_ENTRIES_PER_MODE


def test_a_qualifying_score_reports_its_rank(tmp_path):
    path = tmp_path / "scores.json"
    record_score("modern", HighScore(score=1000, lines=1, level=1), path)
    _, rank = record_score("modern", HighScore(score=2000, lines=1, level=1), path)
    assert rank == 1


def test_a_score_that_misses_the_cut_has_no_rank(tmp_path):
    path = tmp_path / "scores.json"
    for score in range(MAX_ENTRIES_PER_MODE):
        record_score("modern", HighScore(1000 + score, 1, 1), path)
    _, rank = record_score("modern", HighScore(score=1, lines=1, level=1), path)
    assert rank is None


def test_the_two_modes_keep_separate_tables(tmp_path):
    """Classic and modern score on different scales; ranking them together
    would make one of the tables meaningless."""
    path = tmp_path / "scores.json"
    record_score("classic", HighScore(score=100, lines=1, level=1), path)
    record_score("modern", HighScore(score=999, lines=1, level=1), path)
    scores = load_scores(path)
    assert [entry.score for entry in scores["classic"]] == [100]
    assert [entry.score for entry in scores["modern"]] == [999]


def test_saving_to_an_unwritable_location_fails_quietly(tmp_path):
    """A read-only home directory is not a reason to crash right after
    someone finished a good game."""
    unwritable = tmp_path / "no-such-directory" / "scores.json"
    assert save_scores({"modern": []}, unwritable) is False


def test_entries_render_as_a_readable_row():
    row = HighScore(score=1234, lines=42, level=5).as_row()
    assert "1234" in row and "42" in row and "5" in row
