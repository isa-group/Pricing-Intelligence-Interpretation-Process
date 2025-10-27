// Test setup file - Global Jest configuration and utilities
import { afterAll, afterEach, jest } from '@jest/globals';
import fs from 'fs';
import path from 'path';

// Increase timeout for async operations (API calls, file operations)
jest.setTimeout(30000);

// Environment setup
process.env.NODE_ENV = 'test';

// Clean up between tests to ensure test isolation
afterEach(() => {
  jest.clearAllMocks();
  jest.clearAllTimers();
});

// Global cleanup after all tests
afterAll(() => {
  // Clean up any temporary test files
  const testDir = __dirname;
  const tempFiles = fs.readdirSync(testDir).filter(file => 
    file.startsWith('test-') && file.endsWith('.yaml')
  );
  
  tempFiles.forEach(file => {
    try {
      fs.unlinkSync(path.join(testDir, file));
    } catch (error) {
      // Ignore cleanup errors
    }
  });
});

// Global test utilities
declare global {
  var testUtils: {
    createTempFile: (content: string, filename?: string) => string;
    cleanupTempFile: (filepath: string) => void;
    waitFor: (ms: number) => Promise<void>;
    mockConsole: () => void;
    restoreConsole: () => void;
  };
}

// Mock console methods to avoid noise in test output
const originalConsole = { ...console };

(global as any).testUtils = {
  /**
   * Create a temporary file for testing
   */
  createTempFile: (content: string, filename: string = 'temp-test.yaml'): string => {
    const filepath = path.join(__dirname, filename);
    fs.writeFileSync(filepath, content);
    return filepath;
  },

  /**
   * Clean up a temporary file
   */
  cleanupTempFile: (filepath: string): void => {
    try {
      if (fs.existsSync(filepath)) {
        fs.unlinkSync(filepath);
      }
    } catch (error) {
      // Ignore cleanup errors
    }
  },

  /**
   * Wait for a specified number of milliseconds
   */
  waitFor: (ms: number): Promise<void> => {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  /**
   * Mock console methods to reduce test output noise
   */
  mockConsole: (): void => {
    console.log = jest.fn();
    console.error = jest.fn();
    console.warn = jest.fn();
    console.info = jest.fn();
  },

  /**
   * Restore original console methods
   */
  restoreConsole: (): void => {
    console.log = originalConsole.log;
    console.error = originalConsole.error;
    console.warn = originalConsole.warn;
    console.info = originalConsole.info;
  }
};
