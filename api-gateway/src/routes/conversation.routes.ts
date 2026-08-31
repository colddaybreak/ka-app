import { FastifyInstance } from 'fastify';
import { PrismaClient } from '@prisma/client';
import { authenticate } from '../middleware/auth.middleware.js';
import { proxyChatStream } from '../proxy/ai-proxy.js';

const prisma = new PrismaClient();

export default async function conversationRoutes(app: FastifyInstance) {
  app.addHook('preHandler', authenticate);

  // POST /api/conversations — 创建对话
  app.post('/', async (request, reply) => {
    const { knowledgeBaseId, title, systemPrompt, modelConfig } = request.body as any;
    if (!knowledgeBaseId) return reply.code(400).send({ error: '请指定知识库' });

    const kb = await prisma.knowledgeBase.findFirst({ where: { id: knowledgeBaseId } });
    if (!kb) return reply.code(404).send({ error: '知识库不存在' });

    return prisma.conversation.create({
      data: {
        userId: (request.user as any).id,
        knowledgeBaseId,
        title: title || '新对话',
        systemPrompt: systemPrompt || null,
        modelConfig: modelConfig || { model: 'deepseek-v4-flash', temperature: 0.7, maxTokens: 4096 },
      },
    });
  });

  // GET /api/conversations — 列出对话
  app.get('/', async (request) => {
    const userId = (request.user as any).id;
    const role = (request.user as any).role;
    const where = role === 'admin' ? {} : { userId };

    return prisma.conversation.findMany({
      where,
      orderBy: { updatedAt: 'desc' },
      include: {
        knowledgeBase: { select: { id: true, name: true } },
        _count: { select: { messages: true } },
      },
    });
  });

  // GET /api/conversations/:id — 对话详情 + 消息历史
  app.get('/:id', async (request, reply) => {
    const { id } = request.params as any;

    const conv = await prisma.conversation.findFirst({
      where: { id },
      include: {
        knowledgeBase: { select: { id: true, name: true, retrievalConfig: true } },
        messages: { orderBy: { createdAt: 'asc' } },
      },
    });
    if (!conv) return reply.code(404).send({ error: '对话不存在' });
    return conv;
  });

  // PUT /api/conversations/:id — 更新对话
  app.put('/:id', async (request, reply) => {
    const { id } = request.params as any;
    const { title, systemPrompt, modelConfig } = request.body as any;

    return prisma.conversation.update({
      where: { id },
      data: {
        ...(title && { title }),
        ...(systemPrompt !== undefined && { systemPrompt }),
        ...(modelConfig && { modelConfig }),
      },
    });
  });

  // DELETE /api/conversations/:id — 删除对话
  app.delete('/:id', async (request, reply) => {
    const { id } = request.params as any;
    await prisma.conversation.delete({ where: { id } });
    return { success: true };
  });

  // POST /api/conversations/stream — 发送消息（SSE 流式）
  app.post('/stream', async (request, reply) => {
    const { conversationId, message } = request.body as any;
    if (!conversationId || !message) {
      return reply.code(400).send({ error: '请提供 conversationId 和 message' });
    }

    // 加载对话信息和知识库配置
    const conv = await prisma.conversation.findFirst({
      where: { id: conversationId },
      include: { knowledgeBase: true },
    });
    if (!conv) return reply.code(404).send({ error: '对话不存在' });

    const body = {
      conversation_id: conversationId,
      message,
      knowledge_base_id: conv.knowledgeBaseId,
      system_prompt: conv.systemPrompt,
      model_config: conv.modelConfig,
      retrieval_config: conv.knowledgeBase.retrievalConfig,
    };

    await proxyChatStream(request, reply, body);
  });
}
