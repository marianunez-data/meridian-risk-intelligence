"""Small retrieval layer over the project's own documentation (methodology, model card).

TF-IDF is deliberate: the corpus is a few dozen sections, the vocabulary is
domain-specific (PSI, WoE, LGD), and keyword matching is transparent and needs
no embedding API. The interface allows swapping in embeddings later.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


@dataclass
class Passage:
    source: str
    heading: str
    text: str


def load_markdown(paths: list[Path]) -> list[Passage]:
    passages = []
    for path in paths:
        current, buf = path.stem, []
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^#{1,3} ", line):
                if buf and "".join(buf).strip():
                    passages.append(Passage(path.name, current, "\n".join(buf).strip()))
                current, buf = line.lstrip("# ").strip(), []
            else:
                buf.append(line)
        if buf and "".join(buf).strip():
            passages.append(Passage(path.name, current, "\n".join(buf).strip()))
    return passages


class DocIndex:
    def __init__(self, passages: list[Passage]):
        self.passages = passages
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        self.matrix = self.vectorizer.fit_transform([f"{p.heading}\n{p.text}" for p in passages])

    def search(self, query: str, k: int = 3) -> list[tuple[Passage, float]]:
        scores = linear_kernel(self.vectorizer.transform([query]), self.matrix).ravel()
        top = scores.argsort()[::-1][:k]
        return [(self.passages[i], float(scores[i])) for i in top if scores[i] > 0]
