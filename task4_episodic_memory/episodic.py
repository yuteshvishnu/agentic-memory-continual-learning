"""Person 4 (Shubhangi): episodic memory condition that stores and retrieves past task episodes.

Episodic memory retains past task traces or summaries and injects the most relevant
episodes into the prompt for subsequent tasks.

Unlike structured memory, episodic memory performs unstructured recall of prior experiences.
This allows the agent to recall past corrections, but can also cause interference and negative
transfer when rules are over-generalized to exceptions (e.g., over-applying the observation-day
shift to Wingra on T5, or whole-row filtering on T6).
"""

from __future__ import annotations

import json
import re
from typing import Any

from shared.interfaces import Memory

# Stopwords to filter out when computing keyword similarity
STOPWORDS = {
    "a", "about", "after", "all", "an", "and", "are", "as", "at", "be", "before",
    "below", "between", "both", "by", "csv", "data", "decimal", "decimals", "did",
    "do", "does", "during", "each", "file", "files", "find", "for", "from", "get",
    "give", "how", "in", "integer", "into", "is", "it", "its", "many", "much",
    "number", "of", "on", "one", "or", "out", "per", "reply", "result", "the",
    "their", "then", "there", "these", "this", "to", "two", "use", "using", "was",
    "were", "what", "when", "where", "which", "with", "would", "you", "your",
}

# Domain-specific keywords that carry strong retrieval signals
DOMAIN_WEIGHTS = {
    # Stations
    "mendota": 3.0,
    "monona": 3.0,
    "wingra": 3.0,
    # Variables
    "temp": 2.5,
    "temperature": 2.5,
    "water_temp": 2.5,
    "oxygen": 2.5,
    "dissolved_oxygen": 2.5,
    "wind": 2.5,
    "wind_speed": 2.5,
    # Aggregations / qualifiers
    "mean": 2.0,
    "max": 2.0,
    "maximum": 2.0,
    "hours": 2.0,
    "exceeded": 2.0,
    "below": 2.0,
    "daily": 2.0,
    "difference": 2.0,
}


def _tokenize(text: str) -> list[str]:
    """Extract lowercase alphanumeric tokens from text."""
    if not text:
        return []
    return re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())


def _extract_date_keywords(text: str) -> set[str]:
    """Extract specific day patterns like 'july 4', 'july 10', etc."""
    matches = re.findall(r"july\s+\d{1,2}", text.lower())
    return set(matches)


class EpisodicMemory(Memory):
    """Stores full episodes of past tasks and retrieves top-k relevant episodes.

    Attributes:
        max_retrieved: Maximum number of episodes to inject into prompt (default: 2).
        max_code_lines: Maximum lines of code per episode to inject to prevent
            prompt bloat and preserve API budget.
        episodes: List of stored episode dictionaries.
    """

    def __init__(self, max_retrieved: int = 2, max_code_lines: int = 40) -> None:
        self.max_retrieved = max_retrieved
        self.max_code_lines = max_code_lines
        self.episodes: list[dict[str, Any]] = []

    def __len__(self) -> int:
        return len(self.episodes)

    def clear(self) -> None:
        """Reset episodic memory."""
        self.episodes.clear()

    def update(self, task: dict, trace: dict, success: bool) -> None:
        """Store an episode from the completed task.

        Args:
            task: Task dictionary containing 'id', 'prompt', 'files', etc.
            trace: Agent execution trace containing attempts, code, feedback, etc.
            success: Whether the final answer was correct.
        """
        episode = self._build_episode(task=task, trace=trace, success=success)
        self.episodes.append(episode)

    def retrieve(self, task: dict) -> str:
        """Retrieve the most relevant past episodes for the given task.

        Args:
            task: Task dictionary for which to retrieve memories.

        Returns:
            A formatted string of relevant past episodes, or "" if memory is empty.
        """
        if not self.episodes:
            return ""

        ranked_episodes = self._rank_episodes(task)
        if not ranked_episodes:
            return ""

        top_episodes = ranked_episodes[: self.max_retrieved]
        return self._format_episodes_for_prompt(top_episodes)

    def snapshot(self) -> str:
        """Dump the current episode store as a JSON-formatted string."""
        data = {
            "condition": "episodic",
            "total_episodes": len(self.episodes),
            "episodes": self.episodes,
        }
        return json.dumps(data, indent=2)

    # -------------------------------------------------------------------------
    # Internal Helpers: Building, Ranking, and Formatting Episodes
    # -------------------------------------------------------------------------

    def _build_episode(self, task: dict, trace: dict, success: bool) -> dict[str, Any]:
        """Normalize task and trace data into a structured episode record."""
        task_id = str(task.get("id", f"task_{len(self.episodes) + 1}"))
        prompt = str(task.get("prompt", "")).strip()
        files = list(task.get("files", []))

        attempts_data: list[dict[str, Any]] = []
        feedbacks: list[str] = []
        final_code = ""
        final_answer = None

        if isinstance(trace, dict):
            final_answer = trace.get("answer")

            # Check if trace contains an explicit list of attempts
            raw_attempts = trace.get("attempts")
            if isinstance(raw_attempts, list):
                for idx, att in enumerate(raw_attempts, start=1):
                    if isinstance(att, dict):
                        code = str(att.get("code", "")).strip()
                        ans = att.get("answer")
                        feedback = str(att.get("feedback") or att.get("checker_feedback") or "").strip()
                        stdout = str(att.get("stdout") or att.get("output") or "").strip()

                        if feedback:
                            feedbacks.append(feedback)
                        if code:
                            final_code = code

                        attempts_data.append({
                            "attempt": att.get("attempt", idx),
                            "code": code,
                            "answer": ans,
                            "feedback": feedback,
                            "stdout": stdout,
                        })
                    else:
                        attempts_data.append({"attempt": idx, "raw": str(att)})

            # Fallback if trace is a flat dict
            if not final_code:
                final_code = str(trace.get("final_code") or trace.get("code") or "").strip()
            if not feedbacks:
                fb = trace.get("feedback") or trace.get("checker_feedback")
                if isinstance(fb, list):
                    feedbacks.extend([str(f).strip() for f in fb if str(f).strip()])
                elif fb:
                    feedbacks.append(str(fb).strip())

        elif isinstance(trace, list):
            for idx, item in enumerate(trace, start=1):
                if isinstance(item, dict):
                    fb = item.get("feedback")
                    if fb:
                        feedbacks.append(str(fb).strip())
                    code = item.get("code")
                    if code:
                        final_code = str(code).strip()
                    attempts_data.append(item)
                else:
                    attempts_data.append({"attempt": idx, "raw": str(item)})

        elif isinstance(trace, str):
            final_code = trace.strip()

        return {
            "task_id": task_id,
            "prompt": prompt,
            "files": files,
            "success": bool(success),
            "num_attempts": len(attempts_data) if attempts_data else 1,
            "attempts": attempts_data,
            "feedbacks": feedbacks,
            "final_code": final_code,
            "final_answer": final_answer,
        }

    def _score_relevance(self, current_task: dict, episode: dict) -> float:
        """Calculate a relevance score between the current task and a past episode.

        Relevance considers:
        1. Date matching (e.g., both referencing 'july 4')
        2. Station / file overlap (e.g., Mendota, Monona, Wingra)
        3. Domain keyword overlap (variables, aggregations)
        4. General keyword overlap
        5. Small recency bias as a tiebreaker
        """
        curr_prompt = str(current_task.get("prompt", ""))
        ep_prompt = str(episode.get("prompt", ""))

        score = 0.0

        # 1. Date overlap (high signal: e.g. July 4 on T2 and July 4 on T5)
        curr_dates = _extract_date_keywords(curr_prompt)
        ep_dates = _extract_date_keywords(ep_prompt)
        common_dates = curr_dates.intersection(ep_dates)
        if common_dates:
            score += 10.0 * len(common_dates)

        # 2. File and station overlap
        curr_files = {f.lower() for f in current_task.get("files", [])}
        ep_files = {f.lower() for f in episode.get("files", [])}
        if curr_files and ep_files and curr_files.intersection(ep_files):
            score += 6.0

        # 3. Domain keyword overlap
        curr_tokens = set(_tokenize(curr_prompt))
        ep_tokens = set(_tokenize(ep_prompt))
        for token in curr_tokens.intersection(ep_tokens):
            if token in DOMAIN_WEIGHTS:
                score += DOMAIN_WEIGHTS[token]
            elif token not in STOPWORDS:
                score += 1.0

        # 4. Small recency bonus (0.01 per episode index) so later relevant episodes rank higher
        ep_idx = self.episodes.index(episode) if episode in self.episodes else 0
        score += 0.01 * ep_idx

        return score

    def _rank_episodes(self, current_task: dict) -> list[dict]:
        """Rank stored episodes by descending relevance score."""
        scored = [
            (self._score_relevance(current_task, ep), ep)
            for ep in self.episodes
        ]
        # Sort by score descending; if score is tied, preserve order
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [ep for _, ep in scored]

    def _format_episodes_for_prompt(self, episodes: list[dict]) -> str:
        """Format retrieved episodes into context text injected into the agent prompt."""
        sections = [
            "=== PAST EPISODES (EPISODIC MEMORY) ===",
            "Below are prior task episodes you recently completed in this lab.",
        ]

        for ep in episodes:
            task_id = ep.get("task_id", "Unknown")
            prompt = ep.get("prompt", "")
            success = ep.get("success", False)
            feedbacks = ep.get("feedbacks", [])
            final_code = ep.get("final_code", "")
            final_answer = ep.get("final_answer")
            attempts = ep.get("attempts", [])

            status_str = "Solved" if success else "Failed"
            num_attempts = ep.get("num_attempts", 1)

            entry_lines = [
                f"\n--- Episode [{task_id}] ---",
                f"Question: {prompt}",
                f"Result: {status_str} ({num_attempts} attempt{'s' if num_attempts != 1 else ''})",
            ]

            # Highlight reviewer feedbacks received (where lab conventions were revealed)
            if feedbacks:
                entry_lines.append("Feedback received on incorrect attempts:")
                for fb in feedbacks:
                    entry_lines.append(f"  * {fb}")
            elif attempts:
                for att in attempts:
                    fb = att.get("feedback")
                    if fb:
                        ans = att.get("answer", "")
                        entry_lines.append(f"  * Attempt {att.get('attempt')}: answer {ans} -> {fb}")

            # Include the code used, trimmed if necessary to preserve context
            if final_code:
                code_lines = final_code.splitlines()
                if len(code_lines) > self.max_code_lines:
                    trimmed_code = "\n".join(code_lines[: self.max_code_lines]) + "\n# ... [trimmed for length]"
                else:
                    trimmed_code = final_code

                entry_lines.append("Code executed:")
                entry_lines.append("```python")
                entry_lines.append(trimmed_code)
                entry_lines.append("```")

            if final_answer is not None:
                entry_lines.append(f"Final output answer: {final_answer}")

            sections.append("\n".join(entry_lines))

        sections.append("\n=========================================\n")
        return "\n".join(sections)
