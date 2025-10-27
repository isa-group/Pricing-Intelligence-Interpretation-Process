import fs from 'fs';
import path from 'path';

/**
 * Test utilities for API testing
 */
export class TestUtils {
  /**
   * Get test YAML content as string
   */
  static getTestYamlContent(): string {
    return `
pricing:
  name: "Test Pricing Model"
  version: "1.0.0"
  description: "Test pricing configuration for unit tests"
  
  basic_prices:
    small: 10.00
    medium: 25.00
    large: 50.00
    
  multipliers:
    rush_order: 1.5
    weekend: 1.2
    bulk_discount: 0.9
    
  rules:
    - condition: "quantity > 100"
      action: "apply_bulk_discount"
    - condition: "delivery_time < 24h"
      action: "apply_rush_order"
`.trim();
  }

  /**
   * Get test YAML content as Buffer for file uploads
   */
  static getTestYamlBuffer(): Buffer {
    return Buffer.from(this.getTestYamlContent(), 'utf8');
  }

  /**
   * Create a temporary YAML file for testing file uploads (fallback method)
   */
  static createTestYamlFile(filename: string = 'test-pricing.yaml'): string {
    const filepath = path.join(__dirname, filename);
    fs.writeFileSync(filepath, this.getTestYamlContent());
    return filepath;
  }
  
  /**
   * Get invalid YAML content as string
   */
  static getInvalidYamlContent(): string {
    return `
pricing:
  name: "Invalid YAML
  - missing quotes
  invalid: structure
    no: proper: indentation
`;
  }

  /**
   * Get invalid YAML content as Buffer
   */
  static getInvalidYamlBuffer(): Buffer {
    return Buffer.from(this.getInvalidYamlContent(), 'utf8');
  }
  
  /**
   * Create an invalid YAML file for testing error scenarios (fallback method)
   */
  static createInvalidYamlFile(filename: string = 'invalid-pricing.yaml'): string {
    const filepath = path.join(__dirname, filename);
    fs.writeFileSync(filepath, this.getInvalidYamlContent());
    return filepath;
  }
  
  /**
   * Clean up test files
   */
  static cleanupTestFile(filepath: string): void {
    if (fs.existsSync(filepath)) {
      fs.unlinkSync(filepath);
    }
  }
  
  /**
   * Wait for a specified amount of time (for testing async operations)
   */
  static async wait(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  /**
   * Generate a unique test ID
   */
  static generateTestId(): string {
    return `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
