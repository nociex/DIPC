import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Re-export ID generator functions
export { 
  generateStableId, 
  useStableId, 
  generateClientId, 
  useClientId,
  generateFileId 
} from './utils/id-generator'