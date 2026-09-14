import re
from typing import List


class CaptionSplitter:
    """
    Splits narration text into short, highly readable subtitle chunks suitable for YouTube Shorts.
    - Targets 2 to 7 words per caption.
    - Prioritizes natural clause/punctuation boundaries (.,?!;:—).
    - Never breaks words apart.
    - Prevents single-word orphan lines where possible.
    """

    @classmethod
    def split_text(cls, text: str, target_words: int = 4, max_words: int = 7) -> List[str]:
        if not text or not text.strip():
            return []

        cleaned = re.sub(r'\s+', ' ', text.strip())
        all_words = cleaned.split()

        # If overall text is already short enough, return as single chunk
        if len(all_words) <= max_words:
            return [cleaned]

        # 1. First-pass: Split on major punctuation marks if present
        # Keep punctuation attached to the preceding phrase
        raw_clauses = re.split(r'([.,?!;:—]+(?:\s+|$))', cleaned)
        reconstructed_clauses: List[str] = []
        i = 0
        while i < len(raw_clauses):
            part = raw_clauses[i].strip()
            if not part:
                i += 1
                continue
            if i + 1 < len(raw_clauses) and re.match(r'^[.,?!;:—]+', raw_clauses[i + 1].strip()):
                reconstructed_clauses.append(f"{part}{raw_clauses[i + 1].strip()}")
                i += 2
            else:
                reconstructed_clauses.append(part)
                i += 1

        chunks: List[str] = []

        # 2. Sub-chunk each clause if it exceeds max_words
        for clause in reconstructed_clauses:
            clause_words = clause.split()
            if not clause_words:
                continue

            if len(clause_words) <= max_words:
                chunks.append(" ".join(clause_words))
            else:
                # Break long clause into chunks of target_words (approx 3-5 words)
                sub_start = 0
                while sub_start < len(clause_words):
                    remaining = len(clause_words) - sub_start
                    # Avoid leaving 1 orphan word at the end
                    if remaining <= max_words:
                        take = remaining
                    elif remaining == target_words + 1:
                        take = target_words
                    elif remaining - target_words == 1:
                        take = target_words - 1
                    else:
                        take = min(target_words, remaining)

                    chunk_slice = clause_words[sub_start:sub_start + take]
                    chunks.append(" ".join(chunk_slice))
                    sub_start += take

        # 3. Post-pass: Merge awkward 1-word trailing chunks if previous chunk can absorb it
        final_chunks: List[str] = []
        for ch in chunks:
            words = ch.split()
            if len(words) == 1 and final_chunks:
                prev_words = final_chunks[-1].split()
                if len(prev_words) + 1 <= max_words:
                    final_chunks[-1] = f"{final_chunks[-1]} {ch}"
                    continue
            final_chunks.append(ch)

        return final_chunks or [cleaned]
