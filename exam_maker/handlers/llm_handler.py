import time
from exam_maker.logger import app_logger
from exam_maker.config import ASSISTANT_MODEL
from exam_maker.utils.token_tracker import token_tracker

class LLMHandler:
    def __init__(self, client):
        self.client = client
        self.logger = app_logger

    def generate_response(self, prompt, timeout=60, schema=None):
        """
        Generate a response from the LLM and track token usage.
        
        Args:
            prompt (str): The prompt to send to the LLM
            timeout (int): Timeout in seconds
            schema (dict, optional): JSON schema for response format validation
            
        Returns:
            tuple: (The generated response content, usage_info object)
        """
        self.logger.info(f"Generating response with prompt: {prompt[:100]}...")
        start_time = time.time()
        
        try:
            request_params = {
                "model": ASSISTANT_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            if schema:
                request_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "Response",
                        "strict": True,
                        "schema": schema
                    }
                }
            
            response = self.client.chat.completions.create(**request_params)
            
            duration = time.time() - start_time
            self.logger.info(f"Response generated in {duration:.2f} seconds")

            usage_data = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            context = {
                'prompt_length': len(prompt),
                'response_format': 'json_schema' if schema else 'text'
            }
            
            usage_info = token_tracker.track_usage(
                function_name="llm_handler.generate_response",
                model=ASSISTANT_MODEL,
                usage_data=usage_data,
                duration=duration,
                context=context
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error during response generation: {str(e)}")
            return f"Error generating response: {str(e)}"

    def generate_streaming_response(self, prompt):
        """
        Generate a streaming response from the LLM.
        
        Args:
            prompt (str): The prompt to send to the LLM
            
        Yields:
            str: The generated response deltas
        """
        try:
            response_stream = self.client.chat.completions.create(
                model=ASSISTANT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            
            for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
        except Exception as e:
            self.logger.error(f"Error during streaming response: {str(e)}")
            yield f"Error during streaming: {str(e)}" 