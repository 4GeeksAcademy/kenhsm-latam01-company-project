# Diseño del sistema RAG de Brasaland

## 1) Flujo de extremo a extremo

1. Los documentos fuente de Brasaland se almacenan en `docs/company-knowledge-base/`.
2. `setup()` en `data/process/rag.py` recorre cada archivo Markdown, normaliza y fragmenta cada sección en chunks. Cada chunk conserva `company`, `source_document`, `section`, `language`, `chunk_index` y `text`.
3. El mismo módulo genera embeddings con un modelo dedicado de embeddings y los inserta en la colección `brasaland_knowledge` de Qdrant.
4. Cuando llega una pregunta, `query()` ejecuta `retrieve()` para buscar los chunks más relevantes usando la misma estrategia de embeddings.
5. `retrieve()` devuelve solo payloads que superan el umbral `min_score` y excluye resultados irrelevantes.
6. `generate_answer()` arma un prompt con la voz de un vendedor entrenado de Brasaland y solo usa el contexto recuperado. La respuesta final se genera en el LLM de producción, no se devuelve el raw result de Qdrant.
7. El endpoint FastAPI expone `POST /knowledge/query` y responde con `{ "answer": "..." }`.

Diagrama simple:

```text
Documentos fuente
      ↓
setup() -> chunking semántico -> embed() -> Qdrant
      ↓
query() -> retrieve() -> context filtered -> generate_answer() -> respuesta final
```

## 2) Estrategia de chunking

Este corpus tiene cuatro documentos muy distintos en tono y estructura: programa de lealtad, protocolo de desperdicio, guía de alérgenos y procedimiento de compra. Por eso se usó un chunking semántico por párrafos y subsecciones, con un límite de aproximadamente 35 palabras por fragmento y sin cortar reglas o condiciones por la mitad.

Cada chunk se genera a partir de la sección real del documento y conserva su título o subtítulo como `section`. Así, el modelo recibe contexto aún con su origen semántico, evitando fragmentos rotos como una condición seguida de otra parte del procedimiento en un chunk distinto.

## 3) Prácticas de embeddings

- Modelo de embeddings: `text-embedding-3-small` (ID de modelo configurado via variable `FOURGEEKS_EMBEDDING_MODEL`).
- Modelo de generación: `gpt-4o-mini` (ID de modelo configurado via `FOURGEEKS_GENERATION_MODEL`).
- Distancia en Qdrant: `COSINE`.
- Tamaño del vector: 1536.
- Umbral `min_score`: 0.35. Este valor evita forzar contexto irrelevante cuando la consulta no encaja con la base de conocimiento.
- `embed()` se usa de forma consistente en la indexación y en la consulta para que ambas operaciones compartan la misma geometría del espacio vectorial.
- Antes de generar el vector, se normaliza el texto eliminando espacios extra y se usa un fallback determinista en CI o si no hay clave del proveedor.

## 4) Decisiones operativas

- El índice se recrea de forma idempotente en `setup()` para evitar duplicados durante desarrollo.
- Cuando no hay resultados válidos por encima del umbral, la respuesta se formula con honestidad: indica que la base de conocimiento no tiene información suficiente y no inventa hechos de la empresa.
- La respuesta final siempre se genera con el LLM a partir del contexto recuperado; nunca se devuelve un chunk crudo ni una lista de Qdrant.
