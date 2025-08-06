#!/usr/bin/env node
/**
 * Utility script to help update date formatting across all frontend files
 * This script identifies files that need European date formatting updates
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Pages that still need updating based on the grep search results
const filesToUpdate = [
  'pages/OrchestratorPage.tsx',
  'pages/TimelinePage.tsx', 
  'pages/FairnessDashboard.tsx',
  'pages/UserManagement.tsx',
  'pages/TeamManagement.tsx',
  'pages/ProfileManagement.tsx'
];

// Common patterns to replace
const patterns = [
  {
    search: /\.toLocaleDateString\(\)/g,
    replace: 'formatDate(new Date($&))',
    description: 'Replace .toLocaleDateString() with formatDate()'
  },
  {
    search: /\.toLocaleDateString\(['"][^'"]*['"][^)]*\)/g,
    replace: 'formatDate($&)',
    description: 'Replace .toLocaleDateString(locale, options) with formatDate()'
  },
  {
    search: /\.toLocaleString\(\)/g,
    replace: 'formatDateTime(new Date($&))',
    description: 'Replace .toLocaleString() with formatDateTime()'
  },
  {
    search: /\.toLocaleString\(['"][^'"]*['"][^)]*\)/g,
    replace: 'formatDateTime($&)',
    description: 'Replace .toLocaleString(locale, options) with formatDateTime()'
  },
  {
    search: /\.toLocaleTimeString\([^)]*\)/g,
    replace: 'formatTime($&)',
    description: 'Replace .toLocaleTimeString() with formatTime()'
  }
];

function analyzeFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const results = [];
    
    // Check for date formatting patterns
    patterns.forEach(pattern => {
      const matches = content.match(pattern.search);
      if (matches) {
        results.push({
          pattern: pattern.description,
          matches: matches.length,
          examples: matches.slice(0, 3) // Show first 3 examples
        });
      }
    });
    
    // Check if dateUtils is already imported
    const hasDateUtilsImport = content.includes('from \'../utils/dateUtils\'');
    
    return {
      file: filePath,
      needsUpdate: results.length > 0,
      hasDateUtilsImport,
      patterns: results
    };
  } catch (error) {
    return {
      file: filePath,
      error: error.message
    };
  }
}

function generateUpdateInstructions() {
  console.log('=== European Date Formatting Update Plan ===\n');
  
  filesToUpdate.forEach(file => {
    const fullPath = path.join(__dirname, '..', file);
    const analysis = analyzeFile(fullPath);
    
    if (analysis.error) {
      console.log(`❌ ${file}: ${analysis.error}\n`);
      return;
    }
    
    if (!analysis.needsUpdate) {
      console.log(`✅ ${file}: No date formatting patterns found\n`);
      return;
    }
    
    console.log(`📝 ${file}:`);
    console.log(`   Import needed: ${!analysis.hasDateUtilsImport ? 'YES' : 'NO'}`);
    
    if (!analysis.hasDateUtilsImport) {
      console.log(`   Add: import { formatDate, formatDateTime, formatTime } from '../utils/dateUtils';`);
    }
    
    analysis.patterns.forEach(pattern => {
      console.log(`   - ${pattern.pattern} (${pattern.matches} instances)`);
      pattern.examples.forEach(example => {
        console.log(`     Example: ${example}`);
      });
    });
    console.log();
  });
  
  console.log('=== Manual Update Steps ===');
  console.log('1. Add dateUtils import to each file that needs it');
  console.log('2. Replace date formatting patterns with European equivalents:');
  console.log('   - .toLocaleDateString() → formatDate(date)');
  console.log('   - .toLocaleString() → formatDateTime(date)');
  console.log('   - .toLocaleTimeString() → formatTime(date)');
  console.log('3. Test each page to ensure dates display correctly');
  console.log('4. Consider updating date input fields to use European format');
}

// Run the analysis
generateUpdateInstructions();
