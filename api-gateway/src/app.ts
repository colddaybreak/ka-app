import Fastify from 'fastify';
import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import multipart from '@fastify/multipart';
import authRoutes from './routes/auth.routes.js';
import knowledgeBaseRoutes from './routes/knowledge-base.routes.js';
import documentRoutes from './routes/document.routes.js';
import conversationRoutes from './routes/conversation.routes.js';
import dashboardRoutes from './routes/dashboard.routes.js';

export function buildApp() {
  const app = Fastify({ logger: true });

  app.register(cors, { origin: true });
  app.register(jwt, { secret: process.env.JWT_SECRET! });
  app.register(multipart, {
    limits: { fileSize: 50 * 1024 * 1024 }, // 50MB
  });

  // Routes
  app.register(authRoutes, { prefix: '/api/auth' });
  app.register(knowledgeBaseRoutes, { prefix: '/api/knowledge-bases' });
  app.register(documentRoutes, { prefix: '/api/documents' });
  app.register(conversationRoutes, { prefix: '/api/conversations' });
  app.register(dashboardRoutes, { prefix: '/api/dashboard' });

  // Health check
  app.get('/api/health', async () => ({ status: 'ok', service: 'api-gateway' }));

  return app;
}
