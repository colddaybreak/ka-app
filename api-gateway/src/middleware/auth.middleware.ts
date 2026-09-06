import { FastifyRequest, FastifyReply } from 'fastify';

export async function authenticate(request: FastifyRequest, reply: FastifyReply): Promise<boolean> {
  try {
    await request.jwtVerify();
    return true;
  } catch (err) {
    reply.code(401).send({ error: '未授权，请先登录' });
    return false;
  }
}

export async function requireAdmin(request: FastifyRequest, reply: FastifyReply) {
  const ok = await authenticate(request, reply);
  if (!ok) return;
  if ((request.user as any).role !== 'admin') {
    reply.code(403).send({ error: '需要管理员权限' });
  }
}
