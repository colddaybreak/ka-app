// frontend/src/api/chatStream.ts
/**
 * 通过 fetch + ReadableStream 消费 SSE 流式响应
 * （不用 EventSource 是因为 EventSource 不支持 POST）
 */
export async function streamChat(
  body: Record<string, any>,
  token: string,
  callbacks: {
    onToken: (token: string) => void;
    onCitations: (citations: any[]) => void;
    onDone: (fullContent: string) => void;
    onError: (error: string) => void;
  },
) {
  const response = await fetch('/api/conversations/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    callbacks.onError(`请求失败: ${response.status}`);
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      // 解析 SSE 事件：先记录事件类型，再处理对应的 data
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (currentEvent === 'citations') callbacks.onCitations(data);
          else if (data.token) callbacks.onToken(data.token);
          else if (data.error) callbacks.onError(data.error);
          else if (data.full_content) callbacks.onDone(data.full_content);
        } catch {
          /* 忽略解析错误 */
        }
      }
    }
  }
}
