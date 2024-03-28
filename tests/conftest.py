# nothing to see here, yet
import dataclasses as dc
from pathlib import Path
import pytest


DATADIR = Path(__file__).parent / "data"


@pytest.fixture(scope="function")
def resolver(request):
    """return a resolver object to lookup for test data

    Examples:
        >>> def test_me(resolver):
        >>>     print(resolver.lookup("a/b/c")) -> tests/data/a/b/c
    """

    @dc.dataclass
    class Resolver:
        root: Path
        name: str

        def lookup(self, path: Path | str) -> Path:
            candidates = [
                self.root / self.name / path,
                self.root / path,
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
            raise FileNotFoundError(f"cannot find {path}", candidates)

    yield Resolver(DATADIR, request.module.__name__)

