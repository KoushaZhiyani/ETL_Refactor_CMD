import logging as log
from pathlib import Path


class PathGenerateLog:
    """
    Responsible for creating directories if they don't exist.
    This ensures that log files can be safely written to the specified path.
    """

    def __init__(self, path):
        """
        Initialize with the target directory path.

        Args:
            path (str or Path): The directory path to create.
        """
        self.path = path

    def create_address(self) -> None:
        """
        Create the directory specified by self.path.
        - parents=True: create intermediate directories if necessary.
        - exist_ok=True: do not raise error if the directory already exists.
        """
        Path(self.path).mkdir(parents=True, exist_ok=True)


class LoggerConfigurator:
    """
    Configures a file-based logger.
    Responsibilities:
    - Ensure the log directory exists.
    - Create a logger with a FileHandler.
    - Set formatter, log level, file mode, and encoding.
    """

    def __init__(self, dest_path, formater, filemode="a", level=log.INFO, encoding="utf-8"):
        """
        Initialize the logger configurator.

        Args:
            dest_path (str): Path of the log file.
            formater (str): Log message format.
            filemode (str): File mode ('a' for append, 'w' for overwrite). Default is 'a'.
            level (int): Logging level (e.g., log.INFO, log.DEBUG). Default is log.INFO.
            encoding (str): File encoding. Default is 'utf-8'.
        """
        self.dest_path = Path(dest_path)
        self.format = formater
        self.filemode = filemode
        self.level = level
        self.encoding = encoding

    def configure_log(self) -> log.Logger:
        """
        Create and return a logger instance configured with a FileHandler.

        Steps:
        1. Ensure the log directory exists using PathGenerateLog.
        2. Create a logger named after the log file stem.
        3. Set logger level and disable propagation to avoid duplicate logs.
        4. If the logger does not already have a FileHandler, create one with
           the specified formatter, level, filemode, and encoding.
        5. Return the configured logger.

        Returns:
            logging.Logger: Configured logger instance.

        Raises:
            Any exception encountered during file handling or logger configuration.
        """
        try:
            # Ensure the parent directory for the log file exists
            PathGenerateLog(self.dest_path.parent).create_address()

            # Create a logger named after the file (stem) to allow multiple loggers
            logger = log.getLogger(self.dest_path.stem)

            # Set log level and disable propagation to root logger
            logger.setLevel(self.level)
            logger.propagate = False

            # Add a FileHandler only if it doesn't exist yet (prevents duplicates)
            if not any(isinstance(h, log.FileHandler) for h in logger.handlers):
                formatter = log.Formatter(self.format)
                file_handler = log.FileHandler(
                    self.dest_path,
                    mode=self.filemode,
                    encoding=self.encoding
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

            return logger

        except Exception:
            # Re-raise exception with full stack trace for debugging
            raise


class TerminalLog:
    """
    Responsible for adding console output to a logger.
    This allows logs to be printed in real-time to the terminal.
    """

    @staticmethod
    def create_handle(logger: log.Logger) -> None:
        """
        Attach a StreamHandler (console output) to the logger if it doesn't already exist.

        Args:
            logger (logging.Logger): Logger instance to which the console handler will be added.
        """
        # Prevent duplicate StreamHandlers
        if not any(isinstance(h, log.StreamHandler) for h in logger.handlers):
            console_handler = log.StreamHandler()
            console_handler.setLevel(log.INFO)

            console_formatter = log.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)

            logger.addHandler(console_handler)


# ---------------------------
# Example usage:
# ---------------------------
# log_config = LoggerConfigurator(
#     dest_path="logs/etl_pipeline.log",
#     formater="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )
#
# logger = log_config.configure_log()
#
# TerminalLog.create_handle(logger)
#
# logger.info("ETL process started")
# logger.error("Database connection failed")
