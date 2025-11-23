# noqa: E402
"""
ASGI entry point for Vercel serverless deployment.
This file is required by Vercel to properly route requests to FastAPI.
# noqa: E402
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from main import app  # noqa: E402

# Vercel looks for an 'app' variable for ASGI applications
__all__ = ["app"]
