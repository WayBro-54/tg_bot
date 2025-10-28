import sys
import os
import asyncio

# Добавьте текущую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import engine, Base
from models import Submission  # ✅ ВАЖНО: импортируйте модели!

async def init_db():
    """Создаёт все таблицы в БД."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ База данных инициализирована успешно!")
    except Exception as e:
        print(f"❌ Ошибка при инициализации БД: {e}")
    finally:
        await engine.dispose()

# if __name__ == "__main__":
#     asyncio.run(init_db())