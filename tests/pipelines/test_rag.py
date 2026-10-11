from __future__ import annotations

from data.pipelines import rag as rag_module


def test_retrieve_filters_below_threshold(monkeypatch):
    class FakeTrackingClient:
        def search(self, collection_name, query_vector, limit, score_threshold, with_payload):
            assert collection_name == "brasaland_knowledge"
            assert limit == 3
            assert score_threshold == 0.4
            assert with_payload is True
            return [
                {
                    "id": "chunk-1",
                    "score": 0.82,
                    "payload": {
                        "company": "brasaland",
                        "source_document": "loyalty-program",
                        "section": "Programa de lealtad",
                        "language": "es",
                        "chunk_index": 0,
                        "text": "Los clientes pueden acumular Brasa Points al comprar.",
                    },
                },
                {
                    "id": "chunk-2",
                    "score": 0.39,
                    "payload": {
                        "company": "brasaland",
                        "source_document": "waste-protocol",
                        "section": "Desperdicio",
                        "language": "es",
                        "chunk_index": 0,
                        "text": "Se deben separar los residuos orgánicos.",
                    },
                },
                {
                    "id": "chunk-3",
                    "score": 0.71,
                    "payload": {
                        "company": "brasaland",
                        "source_document": "supplier-ordering",
                        "section": "Pedidos",
                        "language": "es",
                        "chunk_index": 0,
                        "text": "Los pedidos deben revisarse antes del cierre del día.",
                    },
                },
            ]

    monkeypatch.setattr(rag_module, "get_qdrant_client", lambda: FakeTrackingClient())
    monkeypatch.setattr(rag_module, "embed", lambda text: [0.1, 0.2, 0.3])

    results = rag_module.retrieve("¿cuántos puntos hay?", k=3, min_score=0.4)

    assert len(results) == 2
    assert [item["source_document"] for item in results] == ["loyalty-program", "supplier-ordering"]
    assert all(item["score"] >= 0.4 for item in results)
    assert all("text" in item for item in results)


def test_query_returns_generated_answer(monkeypatch):
    fake_context = [{
        "company": "brasaland",
        "source_document": "loyalty-program",
        "section": "Programa de lealtad",
        "language": "es",
        "chunk_index": 0,
        "text": "Los clientes acumulan puntos al comprar al contado y con tarjeta.",
    }]

    monkeypatch.setattr(rag_module, "retrieve", lambda *args, **kwargs: fake_context)
    monkeypatch.setattr(rag_module, "generate_answer", lambda question, context: "Respuesta generada por el modelo")

    assert rag_module.query("¿Cómo acumulo puntos?") == "Respuesta generada por el modelo"
