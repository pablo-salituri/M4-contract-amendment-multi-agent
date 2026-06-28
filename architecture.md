# Architecture — Contract Amendment Multi-Agent System

## Objetivo general

Sistema multi-agente que analiza contratos legales y sus enmiendas a partir de imágenes. Recibe dos archivos (contrato original y enmienda), extrae el texto, identifica la estructura documental y devuelve un JSON con las secciones modificadas, los temas afectados y un resumen de los cambios.

El diseño prioriza un pipeline lineal, trazabilidad con Langfuse y salida estructurada validada con Pydantic.

---

## Flujo del pipeline

```text
Imagen original ──► GPT-4o Vision ──► Texto original ──┐
                                                       ├──► Contextualization Agent ──► Mapa contextual ──► Extraction Agent ──► JSON
Imagen enmienda ──► GPT-4o Vision ──► Texto enmienda ┘
```

Etapas ejecutadas en orden fijo, sin ramificaciones ni reintentos automáticos:

1. **Health check** — valida `.env`, credenciales y conectividad con Langfuse.
2. **parse_original_contract** — transcribe la imagen del contrato original.
3. **parse_amendment_contract** — transcribe la imagen de la enmienda.
4. **contextualization_agent** — alinea secciones y estructura entre ambos textos.
5. **extraction_agent** — identifica cambios y produce el output estructurado.

Cada etapa está instrumentada como span hijo del trace raíz `contract-analysis` en Langfuse.

---

## Responsabilidad de cada módulo

| Módulo | Responsabilidad |
| --- | --- |
| `src/main.py` | Punto de entrada CLI; health check y serialización JSON del resultado. |
| `src/health_check.py` | Validación del entorno antes de ejecutar el pipeline. |
| `src/pipeline.py` | Orquestación de etapas, manejo de errores por stage y trazas Langfuse. |
| `src/image_parser.py` | Validación de imágenes, codificación Base64 y llamada a GPT-4o Vision. |
| `src/agents/contextualization_agent.py` | Genera un mapa contextual de alineación estructural entre contratos. |
| `src/agents/extraction_agent.py` | Identifica cambios concretos y devuelve `ContractChangeOutput`. |
| `src/config.py` | Carga de variables de entorno, configuración por etapa y factories de clientes. |
| `src/models.py` | Esquema Pydantic del output final. |
| `src/prompts.py` | Prompts de los agentes (no modificados por esta SPEC). |

---

## Por qué existen dos agentes

La tarea se divide en dos responsabilidades cognitivas distintas:

- **Contextualization Agent** — entiende la estructura de ambos documentos y establece correspondencias entre secciones (alineación, renumeración, secciones nuevas o eliminadas). Produce un mapa intermedio en texto libre.
- **Extraction Agent** — usa ese mapa junto con los textos completos para identificar cambios concretos y emitir el JSON final.

Separar estas tareas reduce la carga por llamada al modelo, mejora la precisión en documentos largos y permite observar cada fase de forma independiente en Langfuse.

---

## Rol de cada tecnología

### GPT-4o Vision

Transcribe imágenes de contratos a texto plano. Se usa vía el SDK de OpenAI (`client.chat.completions.create`) con contenido multimodal (prompt + imagen en Base64). No interpreta ni resume: solo transcribe fielmente.

### LangChain

Abstrae las llamadas a los agentes de texto (`ContextualizationAgent` y `ExtractionAgent`) mediante `ChatOpenAI`. El agente de extracción usa `with_structured_output(ContractChangeOutput)` para forzar la respuesta al esquema Pydantic.

### Pydantic

Define y valida el output final (`ContractChangeOutput`) con campos tipados: `sections_changed`, `topics_touched` y `summary_of_the_change`. Garantiza que la salida del pipeline cumple el contrato de datos acordado.

### Langfuse

Instrumenta el pipeline completo. Cada etapa genera un span con input/output resumido, metadata (modelo, temperatura, versión, etapa) y errores registrados en caso de fallo. Permite auditar ejecuciones sin exponer credenciales ni texto completo de contratos.

---

## Decisiones arquitectónicas

- **Pipeline lineal** — sin loops, reintentos ni ramificaciones. Cada etapa se ejecuta exactamente una vez; un fallo detiene la ejecución inmediatamente.
- **Clientes reutilizables** — `OpenAI`, `Langfuse`, `ChatOpenAI` y los agentes se instancian una vez por ejecución en `create_pipeline_clients()` y se pasan al pipeline.
- **Configuración separada por etapa** — `VisionSettings`, `ContextualizationSettings` y `ExtractionSettings` permiten ajustar modelo, temperatura y tokens de forma independiente vía variables de entorno.
- **Health check previo** — el pipeline no arranca si el entorno o Langfuse no están operativos.
- **Errores tipados por etapa** — `PipelineError` indica en qué stage falló la ejecución, facilitando diagnóstico.
- **Previews en trazas** — Langfuse recibe longitudes y previews truncados, no el texto completo de contratos.

---

## Cómo agregar nuevos agentes

1. Crear el módulo en `src/agents/` con una clase que reciba un `ChatOpenAI` opcional (para reutilización) y su configuración.
2. Agregar prompts en `src/prompts.py` y settings en `src/config.py` (modelo, temperatura, tokens).
3. Registrar una función de stage en `src/pipeline.py` con su span Langfuse y metadata.
4. Insertar la llamada en `run_pipeline()` en el orden lógico del flujo.
5. Instanciar el agente en `create_pipeline_clients()` para evitar recreación innecesaria.

No es necesario modificar `main.py` ni el esquema Pydantic si el nuevo agente es intermedio. Si el agente produce el output final, actualizar `ContractChangeOutput` en una SPEC dedicada.

---

## Ejecución

```bash
# Verificar entorno
python -m src.main

# Ejecutar pipeline
python -m src.main data/test_contracts/documento_1__original.jpg data/test_contracts/documento_1__enmienda.jpg
```
