import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from exam_maker.logger import app_logger


@dataclass
class TokenUsage:
    """Data class to store token usage information"""
    timestamp: str
    function_name: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate: float
    duration_seconds: float
    context: Optional[Dict[str, Any]] = None


class TokenTracker:
    """Centralized token usage tracking and monitoring"""
    
    # OpenAI pricing per 1K tokens (as of 2024)
    PRICING = {
        'gpt-4o': {'input': 0.0025, 'output': 0.01},
        'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
        'assistant_api': {'input': 0.0025, 'output': 0.01},  # Assume gpt-4o pricing for assistant API
    }
    
    def __init__(self):
        self.usage_history: List[TokenUsage] = []
        self.session_total_tokens = 0
        self.session_total_cost = 0.0
        
    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost based on token usage"""
        if model not in self.PRICING:
            # Default to gpt-4o-mini pricing if model not found
            model = 'gpt-4o-mini'
            
        pricing = self.PRICING[model]
        input_cost = (prompt_tokens / 1000) * pricing['input']
        output_cost = (completion_tokens / 1000) * pricing['output']
        return input_cost + output_cost
    
    def track_usage(self, 
                   function_name: str,
                   model: str,
                   usage_data: Dict[str, int],
                   duration: float,
                   context: Optional[Dict[str, Any]] = None) -> TokenUsage:
        """Track token usage for a single LLM call"""
        
        prompt_tokens = usage_data.get('prompt_tokens', 0)
        completion_tokens = usage_data.get('completion_tokens', 0)
        total_tokens = usage_data.get('total_tokens', prompt_tokens + completion_tokens)
        
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        
        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            function_name=function_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_estimate=cost,
            duration_seconds=duration,
            context=context
        )
        
        self.usage_history.append(usage)
        self.session_total_tokens += total_tokens
        self.session_total_cost += cost
        
        # Log the usage
        app_logger.info(
            f"Token Usage - {function_name}: "
            f"{total_tokens} tokens (${cost:.4f}) in {duration:.2f}s"
        )
        
        return usage
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of token usage for current session"""
        return {
            'total_calls': len(self.usage_history),
            'total_tokens': self.session_total_tokens,
            'total_cost': self.session_total_cost,
            'average_tokens_per_call': self.session_total_tokens / len(self.usage_history) if self.usage_history else 0,
            'functions_used': list(set(usage.function_name for usage in self.usage_history))
        }
    
    def get_recent_usage(self, limit: int = 5) -> List[TokenUsage]:
        """Get recent token usage records"""
        return self.usage_history[-limit:]
    
    def format_usage_message(self, usage: TokenUsage) -> str:
        """Format token usage for display in chat interface"""
        estimated_note = " (estimated)" if usage.model == "assistant_api" else ""
        return (
            f"📊 **Token Usage**: {usage.total_tokens} tokens{estimated_note} "
            f"(${usage.cost_estimate:.4f}) in {usage.duration_seconds:.1f}s"
        )
    
    def export_usage_data(self, filepath: str = None) -> str:
        """Export usage data to JSON file"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"logs/token_usage_{timestamp}.json"
        
        data = {
            'session_summary': self.get_session_summary(),
            'usage_history': [asdict(usage) for usage in self.usage_history]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath

    def reset_session(self):
        """Reset token tracking for a new session"""
        self.usage_history.clear()
        self.session_total_tokens = 0
        self.session_total_cost = 0.0
        app_logger.info("Token tracker reset for new session")

    def format_summary(self):
        """Format the session summary into a readable string"""
        summary = self.get_session_summary()
        if summary['total_calls'] == 0:
            return "No LLM calls made yet"
        
        summary_text = (
            f"Total Calls: {summary['total_calls']}\n"
            f"Total Tokens: {summary['total_tokens']:,}\n"
            f"Total Cost: ${summary['total_cost']:.4f}\n"
            f"Avg Tokens/Call: {summary['average_tokens_per_call']:.1f}\n"
            f"Functions Used: {', '.join(summary['functions_used'])}"
        )
        return summary_text


# Global token tracker instance
token_tracker = TokenTracker() 