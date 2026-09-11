import { FastifyInstance } from 'fastify';
import type { MultipartFile } from '@fastify/multipart';
import { PrismaClient } from '@prisma/client';
import { authenticate } from '../middleware/auth.middleware.js';
import { writeFile, mkdir } from 'fs/promises';
import { join, resolve } from 'path';
import { v4 as uuid } from 'uuid';
import { proxyToAI } from '../proxy/ai-proxy.js';

const prisma = new PrismaClient();
// 解析为绝对路径存入数据库，AI 引擎才能跨服务直接读取文件
const UPLOAD_DIR = resolve(process.env.UPLOAD_DIR || './uploads');

export default async function documentRoutes(app: FastifyInstance) {
  app.addHook('preHandler', authenticate);

  // POST /api/documents/upload/:knowledgeBaseId — 上传文档
  app.post('/upload/:knowledgeBaseId', async (request, reply) => {
    const { knowledgeBaseId } = request.params as any;
    const userId = (request.user as any).id;

    const kb = await prisma.knowledgeBase.findFirst({ where: { id: knowledgeBaseId } });
    if (!kb) return reply.code(404).send({ error: '知识库不存在' });
    if ((request.user as any).role !== 'admin' && kb.userId !== userId) {
      return reply.code(403).send({ error: '无权操作' });
    }

    // 遍历 multipart parts：文件 + 可选 metadata(JSON 字符串) + autoExtract(布尔)
    let file: MultipartFile | undefined;
    let metadataRaw: string | undefined;
    let autoExtract = false;
    for await (const part of request.parts()) {
      if (part.type === 'file') {
        file = part;
      } else if (part.fieldname === 'metadata') {
        metadataRaw = String(part.value);
      } else if (part.fieldname === 'autoExtract') {
        autoExtract = part.value === 'true';
      }
    }
    if (!file) return reply.code(400).send({ error: '请选择文件' });

    // 解析元数据：必须是合法 JSON 对象，否则拒绝
    let metadata: any = null;
    if (metadataRaw) {
      try {
        metadata = JSON.parse(metadataRaw);
      } catch {
        return reply.code(400).send({ error: 'metadata 必须为合法 JSON' });
      }
      if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) {
        return reply.code(400).send({ error: 'metadata 必须为 JSON 对象' });
      }
    }

    const ext = file.filename.split('.').pop()?.toLowerCase();
    if (!['pdf', 'txt', 'md', 'docx', 'html'].includes(ext || '')) {
      return reply.code(400).send({ error: '不支持的文件类型，仅支持 PDF/TXT/MD/DOCX/HTML' });
    }

    const docId = uuid();
    const dir = join(UPLOAD_DIR, knowledgeBaseId);
    await mkdir(dir, { recursive: true });
    const filePath = join(dir, `${docId}.${ext}`);

    const buffer = await file.toBuffer();
    await writeFile(filePath, buffer);

    const document = await prisma.document.create({
      data: {
        id: docId,
        knowledgeBaseId,
        filename: file.filename,
        filePath,
        fileSize: buffer.length,
        fileType: ext!,
        status: 'pending',
        metadata: metadata || undefined,
        metadataAutoExtract: autoExtract,
      },
    });

    // 通知 Python 引擎异步处理
    try {
      await proxyToAI(`/ai/documents/${docId}/process`);
    } catch (e) {
      console.error('Failed to trigger document processing:', e);
    }

    return document;
  });

  // GET /api/documents/knowledge-base/:knowledgeBaseId — 文档列表
  app.get('/knowledge-base/:knowledgeBaseId', async (request, reply) => {
    const { knowledgeBaseId } = request.params as any;
    const userId = (request.user as any).id;
    const role = (request.user as any).role;
    // user 角色仅能查看本人知识库下的文档
    const kb = await prisma.knowledgeBase.findFirst({
      where: { id: knowledgeBaseId, ...(role !== 'admin' && { userId }) },
    });
    if (!kb) return reply.code(403).send({ error: '无权访问该知识库' });

    return prisma.document.findMany({
      where: { knowledgeBaseId },
      orderBy: { createdAt: 'desc' },
    });
  });

  // GET /api/documents/:documentId/status — 处理状态
  app.get('/:documentId/status', async (request, reply) => {
    const { documentId } = request.params as any;
    const userId = (request.user as any).id;
    const role = (request.user as any).role;
    const doc = await prisma.document.findFirst({
      where: { id: documentId, knowledgeBase: { userId: role === 'admin' ? undefined : userId } },
    });
    if (!doc) return reply.code(404).send({ error: '文档不存在' });

    if (doc.status === 'processing') {
      try {
        const status = await proxyToAI(`/ai/documents/${documentId}/status`, null, 'GET');
        if (status.status === 'done' || status.status === 'failed') {
          await prisma.document.update({
            where: { id: documentId },
            data: {
              status: status.status,
              chunkCount: status.chunk_count || 0,
              errorMessage: status.error_message,
              processedAt: new Date(),
            },
          });
        }
      } catch { /* Python 引擎不可用时返回本地状态 */ }
    }

    return prisma.document.findUnique({ where: { id: documentId } });
  });

  // PATCH /api/documents/:documentId/metadata — 补充/修改文档元数据
  app.patch('/:documentId/metadata', async (request, reply) => {
    const { documentId } = request.params as any;
    const userId = (request.user as any).id;
    const role = (request.user as any).role;
    const { metadata } = request.body as any;

    if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) {
      return reply.code(400).send({ error: 'metadata 必须为 JSON 对象' });
    }

    const doc = await prisma.document.findFirst({
      where: { id: documentId, knowledgeBase: { userId: role === 'admin' ? undefined : userId } },
    });
    if (!doc) return reply.code(404).send({ error: '文档不存在' });

    // 已入库分块同步刷新元数据，保证检索过滤立即生效
    try {
      await proxyToAI(`/ai/documents/${documentId}/metadata`, { metadata }, 'PUT');
    } catch (e) {
      console.error('Failed to sync chunk metadata:', e);
    }

    return prisma.document.update({ where: { id: documentId }, data: { metadata } });
  });

  // DELETE /api/documents/:documentId — 删除文档
  app.delete('/:documentId', async (request, reply) => {
    const { documentId } = request.params as any;
    const userId = (request.user as any).id;
    const role = (request.user as any).role;

    const doc = await prisma.document.findFirst({
      where: { id: documentId, knowledgeBase: { userId: role === 'admin' ? undefined : userId } },
    });
    if (!doc) return reply.code(404).send({ error: '文档不存在' });

    try { await proxyToAI(`/ai/documents/${documentId}/vectors`, null, 'DELETE'); } catch {}
    await prisma.document.delete({ where: { id: documentId } });
    return { success: true };
  });
}
