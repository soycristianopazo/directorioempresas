import { createContext, useCallback, useContext, useMemo, useState } from 'react';

/**
 * Internacionalización propia, sin librería externa (i18next, react-intl…).
 *
 * Es deliberado, no una carencia: el proyecto arranca con un solo idioma
 * poblado (es-CL) y el catálogo de textos de negocio (categorías, industrias,
 * tipos de documento) vive en tablas de traducción en la base, no en archivos
 * JSON del frontend. Una librería completa de i18n resolvería un problema —
 * pluralización, formatos de fecha por locale— que date-fns con locale 'es' ya
 * cubre para lo que este producto necesita. Si el catálogo de mensajes crece
 * lo suficiente, migrar de este Context a i18next es un cambio contenido: la
 * API pública (`t()`, `locale`, `setLocale`) puede conservarse.
 */

const DEFAULT_LOCALE = 'es-CL';
const STORAGE_KEY = 'directorio.locale';

const dictionaries = {
  'es-CL': {
    'nav.dashboard': 'Panel',
    'nav.company': 'Mi empresa',
    'nav.team': 'Equipo',
    'nav.login': 'Iniciar sesión',
    'nav.register': 'Crear cuenta',
    'nav.logout': 'Cerrar sesión',
    'auth.email': 'Correo corporativo',
    'auth.password': 'Contraseña',
    'auth.invalidCredentials': 'Correo o contraseña incorrectos.',
    'common.loading': 'Cargando…',
    'common.save': 'Guardar cambios',
    'common.cancel': 'Cancelar',
    'common.required': 'Este campo es obligatorio',
  },
};

const I18nContext = createContext(null);

/**
 * Busca la clave en el diccionario.
 *
 * El diccionario es plano a propósito: `{ 'auth.email': '...' }`, no anidado
 * como `{ auth: { email: '...' } }`. Un lookup directo por string es más
 * simple de mantener a mano y evita el error de escribir 'nav.dashboard'
 * pensando que resuelve un objeto anidado que en realidad no existe.
 */
function resolve(dictionary, key) {
  return dictionary[key];
}

/** Interpola {{variable}} dentro de un string ya resuelto. */
function interpolate(template, vars) {
  if (!vars) return template;
  return template.replace(/\{\{(\w+)\}\}/g, (_, name) => (vars[name] !== undefined ? vars[name] : `{{${name}}}`));
}

export function I18nProvider({ children, defaultLocale = DEFAULT_LOCALE }) {
  const [locale, setLocaleState] = useState(
    () => localStorage.getItem(STORAGE_KEY) || defaultLocale,
  );

  const setLocale = useCallback((next) => {
    if (!dictionaries[next]) {
      console.warn(`[I18n] Sin diccionario para "${next}"; se mantiene "${DEFAULT_LOCALE}".`);
      return;
    }
    localStorage.setItem(STORAGE_KEY, next);
    setLocaleState(next);
  }, []);

  const t = useCallback(
    (key, vars) => {
      const dictionary = dictionaries[locale] ?? dictionaries[DEFAULT_LOCALE];
      const value = resolve(dictionary, key);

      if (value === undefined) {
        if (process.env.NODE_ENV !== 'production') {
          console.warn(`[I18n] Falta la clave "${key}" en "${locale}".`);
        }
        return key;
      }

      return interpolate(value, vars);
    },
    [locale],
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, availableLocales: Object.keys(dictionaries) }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error('useI18n() debe usarse dentro de <I18nProvider>');
  }
  return ctx;
}
