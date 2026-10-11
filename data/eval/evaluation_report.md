# Evaluacion tecnica del pronostico de ventas Brasaland

## Estado: pendiente del dataset original

No es posible emitir honestamente un diagnostico de underfitting, overfitting o buen ajuste: `data/raw/brasaland_sales.csv` no esta presente en este checkout. Tampoco se generaron folds con resultados reales ni la curva de aprendizaje. No se usaron datos sustitutos.

Cuando el CSV original este disponible, ejecutar desde la raiz:

```bash
uv run python scripts/evaluate_sales_forecast.py
```

El comando reemplazara este reporte con las metricas observadas, el diagnostico sustentado por los cinco folds temporales y la accion correctiva correspondiente. La curva quedara en `data/eval/learning_curve.png`.

La metrica principal sera MAE en USD, porque expresa el error absoluto mensual tipico para planificar compras. RMSE se reportara tambien para destacar errores grandes que pueden distorsionar pedidos. El contexto disponible no indica que sobreestimar sea mas costoso que subestimar, por lo que ambas metricas son simetricas.