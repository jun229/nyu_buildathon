from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    clerk_jwks_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    
class Config:
    env_file = ".env"
    extra = "ignore"  # Allow extra environment variables

@lru_cache()
def get_settings():
    return Settings()