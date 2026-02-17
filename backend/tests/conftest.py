import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import init_database
from app.detection.text import detector as text_detector_module
from app.main import app
from app.middleware.rate_limiter import rate_limiter
from app.services.analysis_store import analysis_store
from app.services.audit_events import audit_event_store


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def _reset_runtime_state():
    """Isolate stores and disable heavyweight ML loading in tests."""
    old_ml_available = text_detector_module.ML_AVAILABLE
    old_limit = settings.rate_limit_requests
    old_window = settings.rate_limit_window_seconds

    text_detector_module.ML_AVAILABLE = False
    settings.rate_limit_requests = 1000
    settings.rate_limit_window_seconds = 60

    asyncio.run(init_database())
    asyncio.run(analysis_store.reset())
    asyncio.run(audit_event_store.reset())
    rate_limiter._hits.clear()
    rate_limiter._daily_points.clear()

    try:
        yield
    finally:
        text_detector_module.ML_AVAILABLE = old_ml_available
        settings.rate_limit_requests = old_limit
        settings.rate_limit_window_seconds = old_window
        asyncio.run(analysis_store.reset())
        asyncio.run(audit_event_store.reset())
        rate_limiter._hits.clear()
        rate_limiter._daily_points.clear()


# Sample texts for testing
AI_TEXT_SAMPLE = (
    "The integration of artificial intelligence into modern healthcare systems represents "
    "a paradigm shift in how medical professionals approach patient care and diagnosis. "
    "Machine learning algorithms have demonstrated remarkable accuracy in analyzing medical "
    "imaging, often matching or exceeding the performance of experienced radiologists. "
    "These systems process vast datasets of patient information to identify patterns that "
    "might escape human observation, enabling earlier detection of conditions ranging from "
    "cancer to cardiovascular disease. Furthermore, AI-powered predictive models are "
    "transforming preventive medicine by assessing individual risk factors and recommending "
    "personalized intervention strategies."
)

HUMAN_TEXT_SAMPLE = (
    "I was walking down the street yesterday when I bumped into my old friend Sarah. "
    "She looked different -- thinner, maybe, or was it the haircut? We hadn't seen each "
    "other since high school, which feels like a lifetime ago now. 'Oh my god!' she "
    "practically screamed. We ended up grabbing coffee at this tiny place around the corner. "
    "The espresso was terrible but who cares? She told me about her divorce (yikes), her "
    "new job doing something with marine biology, and this cat she adopted named Professor "
    "Whiskers. I couldn't stop laughing. Some things never change."
)
