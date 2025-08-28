# shared/context.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import tiktoken
import time

@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str

@dataclass
class ContextStats:
    tokens_total: int = 0
    tokens_cut: int = 0
    turns: int = 0
    last_reset_at: float = field(default_factory=time.time)


class ContextWindowTracker:
    """
    Per-session, per-agent scoped context with:
      - token counting (tiktoken)
      - soft cap and trimming
      - rolling summaries
    """

    def __init__(self, model: str, soft_cap: int = 12_000, hard_cap: int = 15_000):
        self.enc = tiktoken.encoding_for_model(model) if "gpt" in model else tiktoken.get_encoding("cl100k_base")
        self.soft_cap = soft_cap
        self.hard_cap = hard_cap
        self.stats = ContextStats()
        self.memory_short: List[Message] = []   # rolling working set
        self.memory_summary: Optional[str] = None  # compressed history

    def token_len(self, text: str) -> int:
        return len(self.enc.encode(text or ""))

    def add(self, role: str, content: str):
        self.memory_short.append(Message(role=role, content=content))
        self.stats.turns += 1
    
    def build_prompt(self, system_prompt: str, extra: List[Message] = None) -> List[Dict[str, str]]:
        msgs = [Message(role="system", content=system_prompt)]
        if self.memory_summary:
            msgs.append(Message(role="system", content=f"[Session summary]\n{self.memory_summary}"))
        msgs.extend(self.memory_short)
        if extra:
            msgs.extend(extra)
        # trim if needed
        tokens = sum(self.token_len(m.content) for m in msgs)
        if tokens > self.soft_cap:
            # trim oldest user/assistant messages
            trimmed = []
            for m in msgs:
                trimmed.append(m)
                t = sum(self.token_len(x.content) for x in trimmed)
                if t >= self.hard_cap:
                    break
            self.stats.tokens_cut += tokens - sum(self.token_len(x.content) for x in trimmed)
            msgs = trimmed
        self.stats.tokens_total += sum(self.token_len(m.content) for m in msgs)
        return [dict(role=m.role, content=m.content) for m in msgs]
    
    def update_summary(self, summarizer_fn):
        """
        summarizer_fn(messages: List[Message]) -> str
        Call this every N turns to keep a rolling summary.
        """
        if not self.memory_short:
            return
        self.memory_summary = summarizer_fn(self.memory_short, self.memory_summary)
        self.memory_short = []  # reset short-term after summarizing

    def metrics(self) -> Dict[str, Any]:
        return {
            "tokens_total": self.stats.tokens_total,
            "tokens_cut": self.stats.tokens_cut,
            "turns": self.stats.turns,
            "summary_present": bool(self.memory_summary)
        }