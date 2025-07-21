'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { useLanguage, useTranslation } from '@/lib/i18n/context';
import { Language } from '@/lib/i18n/types';
import { cn } from '@/lib/utils';

interface LanguageToggleProps {
  className?: string;
  variant?: 'default' | 'outline' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  showText?: boolean;
}

export function LanguageToggle({ 
  className, 
  variant = 'ghost', 
  size = 'sm',
  showText = false 
}: LanguageToggleProps) {
  const { language, setLanguage, isLoading } = useLanguage();
  const { t } = useTranslation();

  const handleLanguageToggle = async () => {
    const newLanguage: Language = language === 'zh' ? 'en' : 'zh';
    await setLanguage(newLanguage);
  };

  const getLanguageDisplay = (lang: Language) => {
    return lang === 'zh' ? '中文' : 'EN';
  };

  const getNextLanguageDisplay = () => {
    const nextLang: Language = language === 'zh' ? 'en' : 'zh';
    return getLanguageDisplay(nextLang);
  };

  return (
    <Button
      variant={variant}
      size={size}
      onClick={handleLanguageToggle}
      disabled={isLoading}
      className={cn(
        'transition-all duration-300 ease-in-out hover:scale-105 active:scale-95',
        'min-w-[2.5rem] font-medium relative overflow-hidden',
        'hover:bg-accent/80 focus:ring-2 focus:ring-primary/20',
        isLoading && 'opacity-50 cursor-not-allowed',
        className
      )}
      title={t('nav.language.toggle')}
    >
      <span className="flex items-center gap-1 relative z-10">
        {isLoading ? (
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : (
          <>
            <span 
              className={cn(
                "text-sm font-semibold transition-all duration-300",
                "transform-gpu"
              )}
              key={language} // Force re-render for animation
            >
              {getLanguageDisplay(language)}
            </span>
            {showText && (
              <>
                <span className="text-xs opacity-60 transition-opacity duration-200">→</span>
                <span className="text-xs opacity-60 transition-opacity duration-200">
                  {getNextLanguageDisplay()}
                </span>
              </>
            )}
          </>
        )}
      </span>
      
      {/* Ripple effect on click */}
      <span 
        className={cn(
          "absolute inset-0 bg-primary/10 rounded-md scale-0",
          "transition-transform duration-300 ease-out",
          isLoading && "scale-100"
        )}
      />
    </Button>
  );
}

// Alternative dropdown version for more languages in the future
interface LanguageDropdownProps {
  className?: string;
}

export function LanguageDropdown({ className }: LanguageDropdownProps) {
  const { language, setLanguage, isLoading } = useLanguage();
  const { t } = useTranslation();

  const languages: { value: Language; label: string; nativeLabel: string }[] = [
    { value: 'en', label: 'English', nativeLabel: 'English' },
    { value: 'zh', label: 'Chinese', nativeLabel: '中文' }
  ];

  const currentLanguageInfo = languages.find(lang => lang.value === language);

  return (
    <div className={cn('relative', className)}>
      <Button
        variant="ghost"
        size="sm"
        disabled={isLoading}
        className="flex items-center gap-2 min-w-[4rem]"
        title={t('nav.language.toggle')}
      >
        {isLoading ? (
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : (
          <>
            <span className="text-sm font-medium">
              {currentLanguageInfo?.nativeLabel}
            </span>
            <svg
              className="w-3 h-3 opacity-60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </>
        )}
      </Button>
      
      {/* Dropdown menu would be implemented here with a proper dropdown component */}
      {/* For now, we'll use the simple toggle approach */}
    </div>
  );
}