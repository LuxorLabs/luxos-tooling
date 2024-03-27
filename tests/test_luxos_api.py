from luxos import api


def test_commands():
    assert len(api.COMMANDS) == 57


def test_generate_ip_range():
    ip_addresses = [
        address
        for address in api.generate_ip_range("127.0.0.1", "127.0.0.5")
    ]

    assert len(ip_addresses) == 5
