/**
 * Demo credentials — replace with real auth API in production.
 * Token format matches backend: Authorization: Bearer tenant_<id>
 */
export const DEMO_USERS = [
  {
    email: 'analyst@acme.com',
    password: 'demo1234',
    tenantId: 'acme',
    name: 'J. Doe',
    role: 'Compliance Analyst',
  },
  {
    email: 'admin@acme.com',
    password: 'admin1234',
    tenantId: 'acme',
    name: 'A. Admin',
    role: 'Compliance Admin',
  },
  {
    email: 'analyst@default.com',
    password: 'demo1234',
    tenantId: 'default',
    name: 'M. Singh',
    role: 'Compliance Analyst',
  },
];

export const AUTH_STORAGE_KEY = 'compliance-auth-session';

export function buildBearerToken(tenantId) {
  return `tenant_${tenantId}`;
}
