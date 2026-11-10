# Utilidades de datos Brasaland (Hito 2)

Implementación TypeScript para menú, ventas, locales y desperdicio. Las transformaciones conservan USD y COP como importes paralelos y no convierten ni suman monedas entre sí.

## Verificación

Ejecuta desde la raíz del repositorio:

```sh
npx --yes --package typescript tsc --noEmit -p tsconfig.hito2.json
node --experimental-strip-types --test tests/hito2.test.mjs
```

La suite usa `node:test` y funciona con Node.js 24 o posterior. No requiere instalar dependencias en la raíz.

## Fechas y determinismo

`calculateDailyRevenue` compara el día calendario con una zona IANA opcional; usa UTC si no se indica una. `scoreLocationPerformance` acepta un `asOfDate` opcional y `validateLocation` un `currentYear` opcional para reproducir cálculos y pruebas; si se omiten, toman la fecha/año actuales.
