import { FastifyInstance } from 'fastify';
import { PrismaClient } from '@prisma/client';
import { authenticate } from '../middleware/auth.middleware.js';

const prisma = new PrismaClient();

export default async function dashboardRoutes(app: FastifyInstance) {
  app.addHook('preHandler', authenticate);

  // GET /api/dashboard/stats — 统计卡片
  app.get('/stats', async (request) => {
    const userId = (request.user as any).id;
    const role = (request.user as any).role;
    const where = role === 'admin' ? {} : { userId };

    const [kbCount, docCount, convCount, todayConvCount] = await Promise.all([
      prisma.knowledgeBase.count({ where }),
      prisma.document.count({ where: role === 'admin' ? {} : { knowledgeBase: { userId } } }),
      prisma.conversation.count({ where }),
      prisma.conversation.count({
        where: { ...where, createdAt: { gte: new Date(new Date().toDateString()) } },
      }),
    ]);

    // Token 消耗汇总
    const tokenResult: any = await prisma.$queryRaw`
      SELECT
        COALESCE(SUM((token_usage->>'prompt_tokens')::int), 0) as prompt_tokens,
        COALESCE(SUM((token_usage->>'completion_tokens')::int), 0) as completion_tokens
      FROM messages m
      JOIN conversations c ON m.conversation_id = c.id
      WHERE m.token_usage IS NOT NULL
    `;

    return {
      knowledgeBaseCount: kbCount,
      documentCount: docCount,
      conversationCount: convCount,
      todayConversationCount: todayConvCount,
      tokenUsage: tokenResult[0] || { prompt_tokens: 0, completion_tokens: 0 },
    };
  });

  // GET /api/dashboard/trends?days=30 — 趋势数据
  app.get('/trends', async (request) => {
    const days = Number((request.query as any).days) || 30;
    const userId = (request.user as any).id;
    const isAdmin = (request.user as any).role === 'admin';
    const since = new Date();
    since.setDate(since.getDate() - days);

    const conversations = await prisma.$queryRaw`
      SELECT DATE(created_at) as date, COUNT(*) as count
      FROM conversations
      WHERE created_at >= ${since}
        AND (${isAdmin} OR user_id = ${userId})
      GROUP BY DATE(created_at)
      ORDER BY date
    `;

    return { conversations };
  });
}
