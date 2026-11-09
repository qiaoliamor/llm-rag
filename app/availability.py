"""Fixed transient-service copy; never a model reply or retry instruction to execute."""
BUSY_MESSAGE = '这会儿连接有点慢，先别急，等一会儿再发给我，好吗？'
CHAT_TRANSIENT_CODES = frozenset({'timeout', 'connection', 'upstream_error', 'rate_limit', 'review_busy'})
REVIEW_TRANSIENT_FAILURES = frozenset({'timeout', 'upstream_unavailable', 'rate_limit', 'provider_error'})
