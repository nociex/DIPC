'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Language, I18nContextValue, TranslationKeys } from './types';
import { i18nService } from './service';

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

interface I18nProviderProps {
  children: ReactNode;
  initialLanguage?: Language;
}

export function I18nProvider({ children, initialLanguage }: I18nProviderProps) {
  const [language, setLanguageState] = useState<Language>(
    initialLanguage || i18nService.getCurrentLanguage()
  );
  const [isLoading, setIsLoading] = useState(true);

  // Initialize translations on mount
  useEffect(() => {
    const initializeTranslations = async () => {
      try {
        // Load translations for current language
        await i18nService.loadTranslations(language);
        
        // Preload translations for other language for faster switching
        const otherLanguage: Language = language === 'zh' ? 'en' : 'zh';
        i18nService.loadTranslations(otherLanguage); // Don't await this one
        
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to initialize translations:', error);
        setIsLoading(false);
      }
    };

    initializeTranslations();
  }, [language]);

  // Subscribe to language changes from service
  useEffect(() => {
    const unsubscribe = i18nService.subscribe((newLanguage) => {
      setLanguageState(newLanguage);
    });

    return unsubscribe;
  }, []);

  const setLanguage = async (newLanguage: Language) => {
    if (newLanguage === language) return;
    
    setIsLoading(true);
    try {
      await i18nService.setLanguage(newLanguage);
      setLanguageState(newLanguage);
    } catch (error) {
      console.error('Failed to change language:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const t = (key: keyof TranslationKeys, params?: Record<string, any>): string => {
    return i18nService.t(key, params);
  };

  const contextValue: I18nContextValue = {
    language,
    setLanguage,
    t,
    isLoading
  };

  return (
    <I18nContext.Provider value={contextValue}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (context === undefined) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

// Hook for getting translation function only
export function useTranslation() {
  const { t, language } = useI18n();
  return { t, language };
}

// Hook for language switching
export function useLanguage() {
  const { language, setLanguage, isLoading } = useI18n();
  return { language, setLanguage, isLoading };
}