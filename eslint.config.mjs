import nextPlugin from '@next/eslint-plugin-next';
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

export default [
  { ignores: ['out/**', '.next/**', 'node_modules/**', 'build/**', 'public/models/**', 'public/data/nav.json', 'public/data/scatter.json'] },
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: { '@next/next': nextPlugin },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
];
