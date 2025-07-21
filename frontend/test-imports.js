// Test script to verify module resolution
const path = require('path');
const fs = require('fs');

console.log('Current directory:', process.cwd());
console.log('src/lib exists:', fs.existsSync('./src/lib'));
console.log('src/lib/export-manager.ts exists:', fs.existsSync('./src/lib/export-manager.ts'));

// List all files in src/lib
if (fs.existsSync('./src/lib')) {
  console.log('\nFiles in src/lib:');
  fs.readdirSync('./src/lib').forEach(file => {
    console.log(' -', file);
  });
}