# Test contracts

Images to validate the pipeline. Each pair includes an original contract and its amendment.

## Naming convention

```text
documento_N__original.jpg   → base contract
documento_N__enmienda.jpg   → amendment / addendum
```

Supported formats: `.jpg`, `.jpeg`, `.png`.

## Available pairs

### Pair 1 — `documento_1` (software license agreement)

Expected output:

```json
{
  "sections_changed": [
    "otorgamiento_de_licencia",
    "plazo",
    "pago",
    "soporte",
    "terminacion",
    "proteccion_de_datos"
  ],
  "topics_touched": [
    "canon anual de licencia",
    "soporte tecnico",
    "terminacion del contrato",
    "proteccion de datos"
  ],
  "summary_of_the_change": "El otorgamiento de licencia ahora permite el uso para operaciones internas de negocio. La duración del contrato se extiende de 12 a 24 meses. El canon anual de licencia se incrementa de USD 12.000 a USD 15.000. El soporte técnico se amplía para incluir chat además de correo electrónico. El periodo de notificación para la terminación del contrato se extiende de 30 a 60 días. Se introduce una nueva sección sobre protección de datos, comprometiéndose a cumplir con las normativas aplicables."
}
```

---



### Pair 2 — `documento_2` (professional services agreement)

Expected output:

```json
{
  "sections_changed": [
    "alcance_servicio",
    "duracion",
    "honorarios",
    "entregables",
    "propiedad_intelectual"
  ],
  "topics_touched": [
    "alcance del servicio",
    "duracion contractual",
    "canon mensual de locacion",
    "frecuencia de entregables",
    "propiedad intelectual"
  ],
  "summary_of_the_change": "El alcance del servicio se amplía para incluir análisis regulatorio. La duración del servicio se extiende de 6 a 9 meses. Los honorarios mensuales aumentan de USD 8.000 a USD 9.500. La frecuencia de los entregables cambia de mensual a quincenal. Se introduce una nueva cláusula sobre propiedad intelectual, estableciendo que todos los entregables serán propiedad del Cliente tras el pago final."
}
```

---



### Pair 3 — `documento_3` (SaaS service agreement)

Expected output:

```json
{
  "sections_changed": [
    "precio",
    "disponibilidad_servicio",
    "soporte"
  ],
  "topics_touched": [
    "precio mensual del servicio",
    "disponibilidad del servicio",
    "metodo de soporte al cliente"
  ],
  "summary_of_the_change": "El precio mensual del servicio se incrementa de USD 1.200 a USD 1.250. La disponibilidad del servicio se mejora de 99,5% a 99,9%. El soporte al cliente ahora incluye un sistema de tickets en línea además del correo electrónico."
}
```

---



## Commands

```bash
# Pair 1
python -m src.main data/test_contracts/documento_1__original.jpg data/test_contracts/documento_1__enmienda.jpg

# Pair 2
python -m src.main data/test_contracts/documento_2__original.jpg data/test_contracts/documento_2__enmienda.jpg

# Pair 3
python -m src.main data/test_contracts/documento_3__original.jpg data/test_contracts/documento_3__enmienda.jpg
```

