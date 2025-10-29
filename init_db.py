import sys
import os

# Добавьте текущую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import engine, Base
from models import Submission  # ✅ ВАЖНО: импортируйте модели!


async def init_db():
    """Создаёт все таблицы в БД, если файл БД не существует."""
    try:
        # Получаем путь к файлу БД из URL подключения
        db_url = engine.url.database

        # Проверяем существование файла БД
        if os.path.exists(db_url):
            print(f"✅ Файл базы данных '{db_url}' уже существует. База данных не будет пересоздана.")
            return

        # Если файла нет, создаём все таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ База данных инициализирована успешно!")

    except Exception as e:
        print(f"❌ Ошибка при инициализации БД: {e}")
    finally:
        await engine.dispose()