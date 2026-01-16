import importlib
import logging


def test_root_logger_configuration_and_format() -> None:
    import core.logger as core_logger

    root = logging.getLogger()
    original_handlers = list(root.handlers)
    for handler in original_handlers:
        root.removeHandler(handler)

    try:
        importlib.reload(core_logger)
        logger = core_logger.get_logger("tests.logger")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        handler = root.handlers[0]
        formatter = handler.formatter
        assert formatter is not None
        formatted = formatter.format(
            logging.LogRecord(
                name=logger.name,
                level=logging.INFO,
                pathname=__file__,
                lineno=0,
                msg="message",
                args=(),
                exc_info=None,
            )
        )
        assert "[INFO]" in formatted
        assert "tests.logger - message" in formatted
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        for handler in original_handlers:
            root.addHandler(handler)
