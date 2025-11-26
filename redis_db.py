from redis.asyncio import Redis
import json


class RedisClient:
    def __init__(self):
        self.redis_client = Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

    def ping(self):
        print(self.redis_client.ping())

    async def set_user_data(self, user_id: int, data: dict):
        """Сохранить данные пользователя"""
        await self.redis_client.set(f'{user_id}', json.dumps(data))

    async def get_user_data(self, user_id: int) -> dict:
        """Получить данные пользователя"""
        data = await self.redis_client.get(f"user:{user_id}")
        return json.loads(data) if data else {}

    async def update_user_data(self, user_id: int, **kwargs):
        """Обновить данные пользователя"""
        current_data = await self.get_user_data(user_id)
        current_data.update(kwargs)
        await self.set_user_data(user_id, current_data)

    async def increment_message_count(self, user_id: int):
        """Увеличить счетчик сообщений"""
        await self.redis_client.incr(f"stats:messages:{user_id}")

    async def get_message_count(self, user_id: int) -> int:
        """Получить количество сообщений от пользователя"""
        count = self.redis_client.get(f"stats:messages:{user_id}")
        return int(count) if count else 0

    async def add_to_list(self, user_id: int, item: str):
        """Добавить элемент в список пользователя"""
        self.redis_client.rpush(f"user_list:{user_id}", item)

    async def get_list(self, user_id: int) -> list:
        """Получить список пользователя"""
        return self.redis_client.lrange(f"user_list:{user_id}", 0, -1)