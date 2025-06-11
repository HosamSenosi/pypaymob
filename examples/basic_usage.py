# Simple payment example



# # Example usage configurations
# def create_memory_auth(config: PaymobConfig, connection_pool) -> PaymobAuth:
#     """Create auth instance with memory cache."""
#     return PaymobAuth(config, connection_pool, MemoryCache())


# def create_redis_auth(
#     config: PaymobConfig, connection_pool, redis_client
# ) -> PaymobAuth:
#     """Create auth instance with Redis cache."""
#     return PaymobAuth(config, connection_pool, RedisCache(redis_client))