/**
 * @jest-environment jsdom
 */

import { i18nService } from '../service';
import { Language } from '../types';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock navigator.language
Object.defineProperty(navigator, 'language', {
  writable: true,
  value: 'zh-CN'
});

describe('I18n Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
  });

  describe('Language Detection and Initialization', () => {
    it('should default to Chinese language', () => {
      expect(i18nService.getCurrentLanguage()).toBe('zh');
    });

    it('should detect browser language correctly', () => {
      const detected = i18nService.detectBrowserLanguage();
      expect(detected).toBe('zh');
    });

    it('should use stored language preference', () => {
      localStorageMock.getItem.mockReturnValue('en');
      const service = new (i18nService.constructor as any)();
      expect(service.getCurrentLanguage()).toBe('en');
    });
  });

  describe('Language Switching', () => {
    it('should switch language and persist to localStorage', async () => {
      await i18nService.setLanguage('en');
      
      expect(i18nService.getCurrentLanguage()).toBe('en');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('dipc-language', 'en');
    });

    it('should load translations when switching language', async () => {
      // Mock dynamic import
      const mockTranslations = {
        'nav.settings': 'Settings',
        'nav.language.toggle': 'Switch Language'
      };

      jest.doMock('../translations/en.ts', () => ({
        default: mockTranslations
      }), { virtual: true });

      await i18nService.setLanguage('en');
      
      expect(i18nService.t('nav.settings')).toBe('Settings');
    });
  });

  describe('Translation Function', () => {
    it('should return translation key if translation not found', () => {
      const result = i18nService.t('nonexistent.key' as any);
      expect(result).toBe('nonexistent.key');
    });

    it('should replace parameters in translations', async () => {
      // Mock translation with parameters
      const mockTranslations = {
        'upload.progress.uploading': '正在上传 {{filename}}...'
      };

      jest.doMock('../translations/zh.ts', () => ({
        default: mockTranslations
      }), { virtual: true });

      await i18nService.loadTranslations('zh');
      
      const result = i18nService.t('upload.progress.uploading', { filename: 'test.pdf' });
      expect(result).toBe('正在上传 test.pdf...');
    });
  });

  describe('Formatting Functions', () => {
    it('should format numbers according to language locale', () => {
      i18nService.setLanguage('zh');
      const formatted = i18nService.formatNumber(1234.56);
      expect(formatted).toMatch(/1,234.56|1,234\.56/); // Different locales may format differently
    });

    it('should format dates according to language locale', () => {
      const date = new Date('2024-01-15');
      const formatted = i18nService.formatDate(date);
      expect(formatted).toBeTruthy();
      expect(typeof formatted).toBe('string');
    });

    it('should format currency according to language locale', () => {
      const formatted = i18nService.formatCurrency(100);
      expect(formatted).toMatch(/\$|￥|¥/); // Should contain currency symbol
    });
  });

  describe('Development Features', () => {
    const originalEnv = process.env.NODE_ENV;

    beforeAll(() => {
      process.env.NODE_ENV = 'development';
    });

    afterAll(() => {
      process.env.NODE_ENV = originalEnv;
    });

    it('should log missing translations in development', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      
      i18nService.t('missing.key' as any);
      
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Missing translation for key: missing.key')
      );
      
      consoleSpy.mockRestore();
    });

    it('should store missing translations in localStorage', () => {
      localStorageMock.getItem.mockReturnValue('[]');
      
      i18nService.t('missing.key' as any);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'missing-translations-zh',
        '["missing.key"]'
      );
    });
  });
});