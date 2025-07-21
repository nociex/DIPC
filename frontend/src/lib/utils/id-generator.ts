"use client"

/**
 * SSR-safe ID generation utilities
 * Prevents hydration errors caused by server/client ID mismatches
 */

let counter = 0;

/**
 * Generates stable, sequential IDs that are consistent between server and client
 */
export function generateStableId(prefix: string = 'stable'): string {
  return `${prefix}_${++counter}`;
}

/**
 * React hook for generating stable IDs in components
 */
export function useStableId(prefix: string = 'component'): string {
  const [id] = useState(() => generateStableId(prefix));
  return id;
}

/**
 * Generates client-only IDs safely for SSR environments
 * Returns a placeholder during SSR, real ID on client
 */
export function generateClientId(prefix: string = 'client'): string {
  if (typeof window === 'undefined') {
    // During SSR, return a stable placeholder
    return `${prefix}_ssr_placeholder`;
  }
  // On client, generate time + random ID
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * React hook for generating client-only IDs
 */
export function useClientId(prefix: string = 'client'): string {
  const [id, setId] = useState<string>(() => `${prefix}_ssr_placeholder`);
  
  useEffect(() => {
    // Only generate real ID on client after hydration
    setId(generateClientId(prefix));
  }, [prefix]);
  
  return id;
}

/**
 * Generates file upload IDs that are safe for SSR
 */
export function generateFileId(): string {
  return generateClientId('file');
}

import { useState, useEffect } from 'react';