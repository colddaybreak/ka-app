import { FastifyInstance } from 'fastify';
import bcrypt from 'bcrypt';
import { PrismaClient } from '@prisma/client';
import { authenticate } from '../middleware/auth.middleware.js';

const prisma = new PrismaClient();

export default async function authRoutes(app: FastifyInstance) {
  // POST /api/auth/register
  app.post('/register', async (request, reply) => {
    const { email, password, name } = request.body as any;

    if (!email || !password || !name) {
      return reply.code(400).send({ error: '请填写邮箱、密码和姓名' });
    }

    const exists = await prisma.user.findUnique({ where: { email } });
    if (exists) {
      return reply.code(400).send({ error: '邮箱已注册' });
    }

    const passwordHash = await bcrypt.hash(password, 10);
    const user = await prisma.user.create({
      data: { email, passwordHash, name, role: 'user' },
    });

    const token = app.jwt.sign(
      { id: user.id, email: user.email, role: user.role },
      { expiresIn: process.env.JWT_EXPIRES_IN || '7d' },
    );

    return { token, user: { id: user.id, email, name, role: user.role } };
  });

  // POST /api/auth/login
  app.post('/login', async (request, reply) => {
    const { email, password } = request.body as any;

    const user = await prisma.user.findUnique({ where: { email } });
    if (!user || !(await bcrypt.compare(password, user.passwordHash))) {
      return reply.code(401).send({ error: '邮箱或密码错误' });
    }

    await prisma.user.update({
      where: { id: user.id },
      data: { lastLoginAt: new Date() },
    });

    const token = app.jwt.sign(
      { id: user.id, email: user.email, role: user.role },
      { expiresIn: process.env.JWT_EXPIRES_IN || '7d' },
    );

    return { token, user: { id: user.id, email: user.email, name: user.name, role: user.role } };
  });

  // GET /api/auth/me
  app.get('/me', { preHandler: [authenticate] }, async (request) => {
    const user = await prisma.user.findUnique({
      where: { id: (request.user as any).id },
      select: { id: true, email: true, name: true, role: true, createdAt: true },
    });
    return user;
  });
}
