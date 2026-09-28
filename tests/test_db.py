"""Database session unit tests."""
import pytest
from sqlalchemy import text
from ragbench.db.session import get_session_factory


@pytest.mark.asyncio
async def test_db_session_factory():
    """Verify async database session instantiation and query execution."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
