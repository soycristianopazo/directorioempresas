/**
 * Overrides de Create React App vía Craco.
 *
 * CRA no expone su configuración de webpack/postcss sin "eject". Craco evita
 * el eject y dos cosas que este proyecto necesita:
 *
 *   1. Alias `@` → `src`, para que los imports no dependan de cuántos niveles
 *      de carpeta hay entre el archivo actual y algo en components/ o lib/.
 *
 *   2. El proxy de desarrollo hacia el backend, para que Axios pueda llamar a
 *      rutas relativas y el navegador no tenga que lidiar con CORS en local.
 *      En producción esto no aplica: ahí manda REACT_APP_BACKEND_URL.
 */

const path = require('path');

module.exports = {
  style: {
    postcss: {
      mode: 'extends',
    },
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  devServer: {
    proxy: {
      '/api': {
        target: process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
};
