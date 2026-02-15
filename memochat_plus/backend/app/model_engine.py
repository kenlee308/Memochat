import ollama
from typing import List, Dict, Any

class ModelEngine:
    def __init__(self):
        self.host = "http://127.0.0.1:11434"
        self.client = ollama.Client(host=self.host)
        
    def list_models(self) -> List[Dict[str, Any]]:
        try:
            response = self.client.list()
            raw_models = []
            if isinstance(response, dict):
                raw_models = response.get('models', [])
            else:
                raw_models = getattr(response, 'models', [])
            
            # Normalize to have 'name' and 'size'
            normalized = []
            for m in raw_models:
                # Handle Model objects or dicts
                model_data = m if isinstance(m, dict) else getattr(m, '__dict__', {})
                name = model_data.get('name') or model_data.get('model') or str(m)
                size = model_data.get('size', 0)
                normalized.append({"name": name, "size": size})
            return normalized
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def pull_model(self, model_name: str):
        try:
            return self.client.pull(model_name)
        except Exception as e:
            return {"error": str(e)}

    def generate(self, model: str, prompt: str, system: str = None, temperature: float = 0.7):
        try:
            msgs = []
            if system: msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            response = self.client.chat(model=model, messages=msgs, options={"temperature": temperature})
            return response['message']['content']
        except Exception as e:
            return f"Error generating response: {e}"

    def generate_stream(self, model: str, prompt: str, system: str = None, temperature: float = 0.7):
        """Streams a single prompt generation."""
        try:
            msgs = []
            if system: msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            stream = self.client.chat(model=model, messages=msgs, stream=True, options={"temperature": temperature})
            for chunk in stream:
                yield chunk.get('message', {}).get('content', '')
        except Exception as e:
            yield f"Error in stream: {e}"

    def chat(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7):
        try:
            response = self.client.chat(model=model, messages=messages, options={"temperature": temperature})
            msg = response.get('message', {})
            content = msg.get('content', '')
            thinking = msg.get('thinking', '') or msg.get('reasoning', '')
            
            if thinking:
                return f"<think>\n{thinking}\n</think>\n{content}"
            return content
        except Exception as e:
            return f"Error in chat: {e}"

    def chat_stream(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7):
        try:
            stream = self.client.chat(model=model, messages=messages, stream=True, options={"temperature": temperature})
            in_thinking = False
            
            for chunk in stream:
                msg = chunk.get('message', {})
                thinking = msg.get('thinking', '') or msg.get('reasoning', '')
                content = msg.get('content', '')
                
                # Transition to thinking
                if thinking and not in_thinking:
                    yield "<think>"
                    in_thinking = True
                
                # Transition out of thinking
                if content and in_thinking:
                    yield "</think>"
                    in_thinking = False
                
                if thinking:
                    yield thinking
                if content:
                    yield content
            
            # Close tag if it finished while still thinking
            if in_thinking:
                yield "</think>"
                
        except Exception as e:
            yield f"Error in chat stream: {e}"
