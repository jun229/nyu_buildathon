from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    clerk_jwks_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    environment: str = "development"
    
    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = ""
    elevenlabs_phone_number_id: str = ""   # from ElevenLabs dashboard > Phone Numbers
    
    # Twilio (optional for incoming calls)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra environment variables

@lru_cache()
def get_settings():
    return Settings()