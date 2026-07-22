import os

# The server now validates its production startup prerequisite during import.
os.environ.setdefault("TUSHARE_TOKEN", "test-token")
