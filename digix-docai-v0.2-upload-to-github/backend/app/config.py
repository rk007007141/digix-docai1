from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    cors_origins:str="http://localhost:5173"
    max_upload_mb:int=10
    model_config=SettingsConfigDict(env_file=".env",extra="ignore")
settings=Settings()
