import nextCoreWebVitals from 'eslint-config-next/core-web-vitals'
import nextTypescript from 'eslint-config-next/typescript'
import prettier from 'eslint-config-prettier'

/**
 * Flat config. `eslint-config-next` v16 ya exporta arrays de flat config, así
 * que no hace falta FlatCompat (que además rompe con este paquete por una
 * referencia circular al serializar los plugins).
 */
const config = [
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      'next-env.d.ts',
      'src/lib/supabase/database.types.ts',
      'supabase/.temp/**',
    ],
  },

  ...nextCoreWebVitals,
  ...nextTypescript,
  prettier,

  {
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports', fixStyle: 'inline-type-imports' },
      ],
      // Fuerza a pasar por los helpers de src/lib/supabase, que son los
      // únicos que saben qué cliente corresponde a cada contexto.
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@supabase/supabase-js',
              importNames: ['createClient'],
              message: 'Usa los helpers de src/lib/supabase (server.ts, client.ts o admin.ts).',
            },
          ],
        },
      ],
    },
  },

  {
    // El cliente admin (service_role) es el único autorizado a saltarse RLS.
    files: ['src/lib/supabase/admin.ts'],
    rules: { 'no-restricted-imports': 'off' },
  },
]

export default config
