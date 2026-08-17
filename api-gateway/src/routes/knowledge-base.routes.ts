import { FastifyInstance } from 'fastify';
import { PrismaClient } from '@prisma/client';
import { authenticate } from '../middleware/auth.middleware.js';

const prisma = new PrismaClient();

export default async function knowledgeBaseRoutes(app: FastifyInstance) {
  app.addHook('preHandler', authenticate);

  // POST /api/knowledge-bases — 创建知识库
  app.post('/', async (request, reply) => {
    const { name, description, chunkStrategy, retrievalConfig } = request.body as any;
    if (!name) return reply.code(400).send({ error: '请填写知识库名称' });

    const kb = await prisma.knowledgeBase.create({
      data: {
        name,
        description: description || null,
        userId: (request.user as any).id,
        chunkStrategy: chunkStrategy || { mode: 'recursive', chunkSize: 500, chunkOverlap: 50 },
        retrievalConfig: retrievalConfig || { topK: 5, similarityThreshold: 0.7, useRerank: false },
      },
    });
    return kb;
  });

  // GET /api/knowledge-bases — 列出知识库
  app.get('/', async (request) => {
    const userId = (request.user as any).id;
    const role = (request.user as any).role;
    const where = role === 'admin' ? {} : { userId };

    return prisma.knowledgeBase.findMany({
      where,
      orderBy: { updatedAt: 'desc' },
      include: { _count: { select: { documents: true, conversations: true } } },
    });
  });

  // GET /api/knowledge-bases/:id — 知识库详情
  app.get('/:id', async (request, reply) => {
    const { id } = request.params as any;
    const kb = await prisma.knowledgeBase.findFirst({
      where: { id },
      include: {
        documents: { orderBy: { createdAt: 'desc' } },
        _count: { select: { documents: true, conversations: true } },
      },
    });
    if (!kb) return reply.code(404).send({ error: '知识库不存在' });
    return kb;
  });

  // PUT /api/knowledge-bases/:id — 更新知识库
  app.put('/:id', async (request, reply) => {
    const { id } = request.params as any;
    const userId = (request.user as any).id;
    const role = (request.user as any).role;

    const existing = await prisma.knowledgeBase.findFirst({ where: { id } });
    if (!existing) return reply.code(404).send({ error: '知识库不存在' });
    if (role !== 'admin' && existing.userId !== userId) {
      return reply.code(403).send({ error: '无权操作' });
    }

    const { name, description, chunkStrategy, retrievalConfig } = request.body as any;
    return prisma.knowledgeBase.update({
      where: { id },
      data: {
        ...(name && { name }),
        ...(description !== undefined && { description }),
        ...(chunkStrategy && { chunkStrategy }),
        ...(retrievalConfig && { retrievalConfig }),
      },
    });
  });

  // DELETE /api/knowledge-bases/:id — 删除知识库
  app.delete('/:id', async (request, reply) => {
    const { id } = request.params as any;
    const userId = (request.user as any).id;
    const role = (request.user as any).role;

    const existing = await prisma.knowledgeBase.findFirst({ where: { id } });
    if (!existing) return reply.code(404).send({ error: '知识库不存在' });
    if (role !== 'admin' && existing.userId !== userId) {
      return reply.code(403).send({ error: '无权操作' });
    }

    // 级联删除（Prisma schema 中已配置 onDelete: Cascade）
    await prisma.knowledgeBase.delete({ where: { id } });
    return { success: true };
  });
}
