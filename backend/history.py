"""History management: truncate + async summarization."""
from backend.llm import call_llm
from backend.protocol import Message, Participant
from backend.prompt import build_summarizer_prompt

# Thresholds
RECENT_KEEP = 10          # keep last N messages intact
TOKEN_TRIGGER = 8000      # trigger summarization when full text exceeds this


class HistoryManager:
    def __init__(self, summarizer: Participant | None = None):
        self.summarizer = summarizer
        self.summary = ""
        self._summarizing = False

    def get_context(self, history: list[Message], target_name: str) -> list[Message]:
        """
        Build the message context for a participant.
        Main agent always gets full history.
        Participants get summary + recent messages (only when @'d).
        """
        # For main agent or when target is all — return everything
        if target_name == "all":
            return history

        # Summary + recent messages
        recent = history[-RECENT_KEEP:]
        context = []
        if self.summary:
            context.append(Message(
                sender="[系统摘要]",
                content=self.summary,
            ))
        context.extend(recent)
        return context

    def should_summarize(self, history: list[Message]) -> bool:
        """Check if summarization is needed based on token threshold."""
        if self._summarizing:
            return False
        text = " ".join(m.content for m in history)
        return len(text) // 4 > TOKEN_TRIGGER

    def summarize(self, history: list[Message]) -> bool:
        """Run summarization using the summarizer LLM. Returns True if successful."""
        if self.summarizer is None or self._summarizing:
            return False
        if not self.should_summarize(history):
            return False

        self._summarizing = True
        split = max(0, len(history) - RECENT_KEEP)
        old_messages = history[:split]

        prompt = build_summarizer_prompt(self.summary, old_messages)

        try:
            new_summary = call_llm(
                model=self.summarizer.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.summarizer.api_key,
                base_url=self.summarizer.base_url,
                temperature=0.3,
            )
            self.summary = new_summary
            return True
        except Exception:
            return False
        finally:
            self._summarizing = False
