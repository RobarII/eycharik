"""Job kind names are a contract between producers and the worker.

Keeping them in one dependency-free module means an API use case never imports the worker, and the
worker never guesses a spelling.
"""

EXTRACT_DOCUMENT = "extract_document"
INDEX_DOCUMENT = "index_document"
START = "start"
MESSAGE = "message"
TIMEOUT = "timeout"
