from pathlib import Path

def test_import():
    """makes sure we're importing the correct luxos package
    """

    from luxos import api
    assert (Path(api.__file__).parent / "api.json").exists()

    assert len(api.COMMANDS) == 57
