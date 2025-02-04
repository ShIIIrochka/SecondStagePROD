# -*- coding: utf-8 -*-


def get_pretty_erros() -> None:
    """Утилита для вызова pretty_errors"""

    try:
        import pretty_errors  # noqa
    except ImportError:
        pass
