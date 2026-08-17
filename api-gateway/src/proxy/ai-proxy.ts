import axios from 'axios';
import { FastifyRequest, FastifyReply } from 'fastify';

const AI_ENGINE_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';
const INTERNAL_TOKEN = process.env.INTERNAL_API_TOKEN || '';

/**
 * SSE 透明代理：将对话请求转发到 Python AI 引擎，逐 chunk 回传给前端
 */
export async function proxyChatStream(
  request: FastifyRequest,
  reply: FastifyReply,
  body: Record<string, any>,
) {
  reply.raw.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  try {
    const response = await axios.post(`${AI_ENGINE_URL}/ai/chat/stream`, body, {
      headers: {
        'X-Internal-Token': INTERNAL_TOKEN,
        'X-User-Id': (request.user as any).id,
        'Content-Type': 'application/json',
      },
      responseType: 'stream',
    });

    response.data.on('data', (chunk: Buffer) => {
      reply.raw.write(chunk);
    });

    response.data.on('end', () => {
      reply.raw.end();
    });

    response.data.on('error', (err: Error) => {
      console.error('AI engine stream error:', err);
      reply.raw.write(`data: ${JSON.stringify({ error: 'AI 服务连接中断' })}\n\n`);
      reply.raw.end();
    });
  } catch (error: any) {
    reply.raw.write(`data: ${JSON.stringify({ error: 'AI 服务暂时不可用' })}\n\n`);
    reply.raw.end();
  }
}

/**
 * 同步代理：管理操作转发到 Python AI 引擎
 */
export async function proxyToAI(path: string, body?: any, method: string = 'POST') {
  const response = await axios({
    method,
    url: `${AI_ENGINE_URL}${path}`,
    headers: { 'X-Internal-Token': INTERNAL_TOKEN },
    data: body,
    timeout: 30000,
  });
  return response.data;
}
