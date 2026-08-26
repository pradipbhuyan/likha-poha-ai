import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // Ignore build output and generated directories
  globalIgnores(['dist', 'coverage', '.vitest-cache']),

  // ── Main source files ─────────────────────────────────────────────────────
  {
    files: ['**/*.{js,jsx}'],
    ignores: ['**/*.test.{js,jsx}', '**/tests/**'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // ── React Hooks v7 introduced very strict new rules that require large
      //    refactors across the codebase. Disable the most aggressive ones for now.
      'react-hooks/set-state-in-effect': 'off',

      // ── ESLint v10 new rules ──────────────────────────────────────────────
      // preserve-caught-error: good practice but many existing catch blocks
      // intentionally re-throw without forwarding the cause. Disable for now.
      'preserve-caught-error': 'off',
      // no-useless-assignment: legitimate patterns like initialising a
      // polling variable before a loop (let latestJob = null).
      'no-useless-assignment': 'warn',

      // ── Unused variables ─────────────────────────────────────────────────
      // Keep the rule but make it lenient:
      //   • caughtErrors:"none"    — don't flag catch(err) bindings
      //   • ignoreRestSiblings     — allow {file, ...rest} destructuring
      //   • varsIgnorePattern      — allow _-prefixed throwaway names
      'no-unused-vars': ['warn', {
        vars: 'all',
        args: 'after-used',
        caughtErrors: 'none',
        ignoreRestSiblings: true,
        varsIgnorePattern: '^_',
        argsIgnorePattern: '^_',
      }],

      // ── React Refresh ─────────────────────────────────────────────────────
      // Context files (ToastContext) and utility files (StructuredVisualBlock)
      // legitimately export both components and helper functions/hooks.
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],

      // ── Regex escapes ────────────────────────────────────────────────────
      // markdownCleanup.js uses intentional escapes inside complex patterns.
      'no-useless-escape': 'warn',
    },
  },

  // ── Root-level Node config files ─────────────────────────────────────────
  // playwright.config.js, vite.config.js, etc. run under Node, not the
  // browser — they need `process`/`__dirname`/etc., not window/document.
  // CI's `eslint src/ --max-warnings 50` never lints these anyway, but
  // `eslint .` (what a contributor runs locally, and what this project's
  // own lint script covers) does, so they still need to pass cleanly.
  {
    files: ['*.config.js', '*.config.mjs', '*.config.cjs'],
    extends: [js.configs.recommended],
    languageOptions: {
      globals: globals.node,
    },
  },

  // ── Test files ────────────────────────────────────────────────────────────
  // Vitest injects globals (describe, test, expect, …) at runtime.
  // Tell ESLint about them so it doesn't flag them as undefined.
  {
    files: ['**/*.test.{js,jsx}', '**/tests/**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
    ],
    languageOptions: {
      globals: {
        ...globals.browser,
        // Vitest globals
        describe:   'readonly',
        it:         'readonly',
        test:       'readonly',
        expect:     'readonly',
        beforeEach: 'readonly',
        afterEach:  'readonly',
        beforeAll:  'readonly',
        afterAll:   'readonly',
        vi:         'readonly',
      },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      'react-hooks/set-state-in-effect': 'off',
      'preserve-caught-error': 'off',
      'no-unused-vars': ['warn', {
        caughtErrors: 'none',
        ignoreRestSiblings: true,
        varsIgnorePattern: '^_',
        argsIgnorePattern: '^_',
      }],
      'no-useless-escape': 'warn',
    },
  },
])
