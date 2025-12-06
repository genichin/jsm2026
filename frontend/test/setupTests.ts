import '@testing-library/jest-dom';
import { beforeAll, afterEach, afterAll } from 'vitest';
import { server } from './mocks/server';

// Establish API mocking before all tests.
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));

// Reset any request handlers that are declared during tests.
afterEach(() => server.resetHandlers());

// Clean up after all tests are finished.
afterAll(() => server.close());
