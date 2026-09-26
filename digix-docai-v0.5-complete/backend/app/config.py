from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 10
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ocr_max_width: int = 2400
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
