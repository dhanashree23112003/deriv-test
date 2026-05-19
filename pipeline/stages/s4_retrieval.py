import json
from pathlib import Path
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pipeline.models import KBArticle, PreprocessedTicket, RetrievedArticle, TicketRetrieval

OUTPUT_FILE = "retrieval_results.json"
TOP_K = 2


def _article_text(article: KBArticle) -> str:
    tags_str = " ".join(article.tags)
    return f"{article.title} {article.body} {tags_str}"


def _ticket_text(ticket: PreprocessedTicket) -> str:
    return f"{ticket.subject_for_processing} {ticket.message_for_processing}"


def retrieve_articles(
    tickets: List[PreprocessedTicket],
    articles: List[KBArticle],
) -> List[TicketRetrieval]:
    corpus = [_article_text(a) for a in articles]
    queries = [_ticket_text(t) for t in tickets]

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    all_texts = corpus + queries
    vectorizer.fit(all_texts)

    article_matrix = vectorizer.transform(corpus)
    query_matrix = vectorizer.transform(queries)

    similarity_matrix = cosine_similarity(query_matrix, article_matrix)

    results: List[TicketRetrieval] = []
    for i, ticket in enumerate(tickets):
        scores = similarity_matrix[i]
        top_indices = np.argsort(scores)[::-1][:TOP_K]
        retrieved = [
            RetrievedArticle(
                article_id=articles[idx].article_id,
                title=articles[idx].title,
                score=round(float(scores[idx]), 4),
            )
            for idx in top_indices
        ]
        results.append(TicketRetrieval(ticket_id=ticket.ticket_id, retrieved_articles=retrieved))

    Path(OUTPUT_FILE).write_text(
        json.dumps([r.model_dump() for r in results], indent=2),
        encoding="utf-8",
    )
    print(f"  Retrieved top-{TOP_K} articles for {len(results)} tickets -> {OUTPUT_FILE}")
    return results
