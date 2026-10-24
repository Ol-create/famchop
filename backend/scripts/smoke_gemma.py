"""Run from backend/:  python -m scripts.smoke_gemma"""

from app.ai import ask_ai
from app.config import get_settings

if __name__ == "__main__":
    print(f"Model: {get_settings().gemma_model}\n")
    print(ask_ai("Suggest 3 cheap Nigerian breakfast meals. One line each."))
