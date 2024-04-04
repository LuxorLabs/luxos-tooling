from pathlib import Path

def test_import():
    """makes sure we're importing the correct luxos package
    """

    from luxos import api
    assert (Path(api.__file__).parent / "api.json").exists()

    assert len(api.COMMANDS) == 57


def test_logon_required():
    from luxos import api

    assert api.logon_required("blah") is None
    assert api.logon_required("logoff") is True
    assert api.logon_required("logon") is False
