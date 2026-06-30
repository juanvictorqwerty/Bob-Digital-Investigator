declare module "bun:test" {
  export function describe(name: string, fn: () => void): void;
  export function it(name: string, fn: () => void | Promise<void>): void;
  export function expect<T>(actual: T): {
    toBe(expected: T): void;
    toBeTruthy(): void;
    toBeNull(): void;
    toContain(expected: string): void;
    toBeGreaterThan(expected: number): void;
    toBeLessThan(expected: number): void;
    toBeGreaterThanOrEqual(expected: number): void;
    toBeLessThanOrEqual(expected: number): void;
    toBeInstanceOf(expected: new (...args: any[]) => any): void;
    toEqual(expected: T): void;
    toHaveLength(expected: number): void;
    toMatch(expected: RegExp | string): void;
    toThrow(expected?: any): void;
    toHaveProperty(property: string, value?: any): void;
  };
  export function afterEach(fn: () => void | Promise<void>): void;
  export function beforeEach(fn: () => void | Promise<void>): void;
  export const mock: {
    (): any;
    (...args: any[]): any;
  };
  export function spyOn(obj: any, method: string): {
    mockImplementation(fn: (...args: any[]) => any): any;
    mockReturnValue(value: any): any;
    mockResolvedValue(value: any): any;
    mockRejectedValue(value: any): any;
    calls: { args: any[] }[];
  };
}