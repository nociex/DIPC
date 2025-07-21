import { Language, TranslationKeys, I18nServiceConfig } from './types';

export class I18nService {
  private translations: Record<Language, Partial<TranslationKeys>> = {
    zh: {},
    en: {}
  };
  
  private currentLanguage: Language;
  private config: I18nServiceConfig;
  private listeners: Set<(language: Language) => void> = new Set();

  constructor(config: Partial<I18nServiceConfig> = {}) {
    this.config = {
      defaultLanguage: 'en',
      fallbackLanguage: 'en',
      storageKey: 'dipc-language',
      detectBrowserLanguage: true,
      ...config
    };

    // Initialize language
    this.currentLanguage = this.initializeLanguage();
  }

  /**
   * Initialize language based on stored preference, browser detection, or default
   */
  private initializeLanguage(): Language {
    // Check localStorage first
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(this.config.storageKey) as Language;
      if (stored && this.isValidLanguage(stored)) {
        return stored;
      }

      // Detect browser language if enabled
      if (this.config.detectBrowserLanguage) {
        const detected = this.detectBrowserLanguage();
        if (detected) {
          return detected;
        }
      }
    }

    return this.config.defaultLanguage;
  }

  /**
   * Detect browser language preference
   */
  detectBrowserLanguage(): Language | null {
    if (typeof window === 'undefined') return null;

    const browserLang = navigator.language || (navigator as any).userLanguage;
    
    // Check for exact matches first
    if (browserLang === 'zh' || browserLang === 'zh-CN' || browserLang === 'zh-Hans') {
      return 'zh';
    }
    
    if (browserLang === 'en' || browserLang.startsWith('en-')) {
      return 'en';
    }

    // Check language prefix
    const langPrefix = browserLang.split('-')[0];
    if (langPrefix === 'zh') return 'zh';
    if (langPrefix === 'en') return 'en';

    return null;
  }

  /**
   * Check if language is valid
   */
  private isValidLanguage(lang: string): lang is Language {
    return lang === 'zh' || lang === 'en';
  }

  /**
   * Load translations for a specific language
   */
  async loadTranslations(language: Language): Promise<void> {
    try {
      // Dynamic import based on language
      const translations = await import(`./translations/${language}.ts`);
      this.translations[language] = translations.default;
    } catch (error) {
      console.warn(`Failed to load translations for ${language}:`, error);
      
      // If loading fails and it's not the fallback language, try fallback
      if (language !== this.config.fallbackLanguage) {
        try {
          const fallbackTranslations = await import(`./translations/${this.config.fallbackLanguage}.ts`);
          this.translations[language] = fallbackTranslations.default;
        } catch (fallbackError) {
          console.error(`Failed to load fallback translations:`, fallbackError);
        }
      }
    }
  }

  /**
   * Get current language
   */
  getCurrentLanguage(): Language {
    return this.currentLanguage;
  }

  /**
   * Set current language
   */
  async setLanguage(language: Language): Promise<void> {
    if (!this.isValidLanguage(language)) {
      console.warn(`Invalid language: ${language}`);
      return;
    }

    // Load translations if not already loaded
    if (!this.translations[language] || Object.keys(this.translations[language]).length === 0) {
      await this.loadTranslations(language);
    }

    this.currentLanguage = language;

    // Persist to localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem(this.config.storageKey, language);
    }

    // Notify listeners
    this.listeners.forEach(listener => listener(language));
  }

  /**
   * Subscribe to language changes
   */
  subscribe(listener: (language: Language) => void): () => void {
    this.listeners.add(listener);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Translate a key with optional parameters
   */
  t(key: keyof TranslationKeys, params?: Record<string, any>): string {
    const currentTranslations = this.translations[this.currentLanguage];
    const fallbackTranslations = this.translations[this.config.fallbackLanguage];
    
    // Get translation from current language or fallback
    let translation = currentTranslations?.[key] || fallbackTranslations?.[key];
    
    // If no translation found, return the key in development
    if (!translation) {
      this.handleMissingTranslation(key, this.currentLanguage);
      return key;
    }

    // Replace parameters if provided
    if (params && translation) {
      Object.entries(params).forEach(([paramKey, value]) => {
        const placeholder = `{{${paramKey}}}`;
        translation = translation!.replace(new RegExp(placeholder, 'g'), String(value));
      });
    }

    return translation;
  }

  /**
   * Handle missing translation detection and logging
   */
  private handleMissingTranslation(key: keyof TranslationKeys, language: Language): void {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`Missing translation for key: ${key} in language: ${language}`);
      
      // Store missing translations for development tools
      if (typeof window !== 'undefined') {
        const missingKey = `missing-translations-${language}`;
        const existing = JSON.parse(localStorage.getItem(missingKey) || '[]');
        if (!existing.includes(key)) {
          existing.push(key);
          localStorage.setItem(missingKey, JSON.stringify(existing));
        }
      }
    }
  }

  /**
   * Validate translation completeness (development only)
   */
  validateTranslations(): { language: Language; missingKeys: string[] }[] {
    if (process.env.NODE_ENV !== 'development') {
      return [];
    }

    const results: { language: Language; missingKeys: string[] }[] = [];
    const languages = this.getAvailableLanguages();
    
    // Get all possible keys from type definition
    const allKeys = Object.keys(this.translations.en || {}) as (keyof TranslationKeys)[];
    
    languages.forEach(language => {
      const translations = this.translations[language];
      const missingKeys: string[] = [];
      
      allKeys.forEach(key => {
        if (!translations?.[key]) {
          missingKeys.push(key);
        }
      });
      
      if (missingKeys.length > 0) {
        results.push({ language, missingKeys });
      }
    });
    
    return results;
  }

  /**
   * Get missing translations from localStorage (development only)
   */
  getMissingTranslations(language: Language): string[] {
    if (process.env.NODE_ENV !== 'development' || typeof window === 'undefined') {
      return [];
    }
    
    const missingKey = `missing-translations-${language}`;
    return JSON.parse(localStorage.getItem(missingKey) || '[]');
  }

  /**
   * Clear missing translations log (development only)
   */
  clearMissingTranslations(language?: Language): void {
    if (process.env.NODE_ENV !== 'development' || typeof window === 'undefined') {
      return;
    }
    
    if (language) {
      localStorage.removeItem(`missing-translations-${language}`);
    } else {
      this.getAvailableLanguages().forEach(lang => {
        localStorage.removeItem(`missing-translations-${lang}`);
      });
    }
  }

  /**
   * Format number according to current language locale
   */
  formatNumber(num: number, options?: Intl.NumberFormatOptions): string {
    const locale = this.currentLanguage === 'zh' ? 'zh-CN' : 'en-US';
    return new Intl.NumberFormat(locale, options).format(num);
  }

  /**
   * Format date according to current language locale
   */
  formatDate(date: Date, options?: Intl.DateTimeFormatOptions): string {
    const locale = this.currentLanguage === 'zh' ? 'zh-CN' : 'en-US';
    return new Intl.DateTimeFormat(locale, options).format(date);
  }

  /**
   * Format currency according to current language locale
   */
  formatCurrency(amount: number, currency: string = 'USD'): string {
    const locale = this.currentLanguage === 'zh' ? 'zh-CN' : 'en-US';
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  /**
   * Get all available languages
   */
  getAvailableLanguages(): Language[] {
    return ['zh', 'en'];
  }

  /**
   * Check if translations are loaded for current language
   */
  isTranslationsLoaded(language?: Language): boolean {
    const lang = language || this.currentLanguage;
    return !!(this.translations[lang] && Object.keys(this.translations[lang]).length > 0);
  }

  /**
   * Preload translations for all languages
   */
  async preloadAllTranslations(): Promise<void> {
    const languages = this.getAvailableLanguages();
    await Promise.all(languages.map(lang => this.loadTranslations(lang)));
  }
}

// Create singleton instance with Chinese as default
export const i18nService = new I18nService({
  defaultLanguage: 'zh',
  fallbackLanguage: 'en'
});