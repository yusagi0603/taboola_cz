from openai import OpenAI
from exam_maker.config import OPENAI_API_KEY

# Initialize OpenAI client
llm_client = OpenAI(api_key=OPENAI_API_KEY)
