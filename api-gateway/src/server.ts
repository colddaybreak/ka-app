import { buildApp } from './app.js';
import dotenv from 'dotenv';
dotenv.config();

const app = buildApp();
const PORT = Number(process.env.PORT) || 3000;

app.listen({ port: PORT, host: '0.0.0.0' })
  .then(() => console.log(`🚀 API Gateway running on http://localhost:${PORT}`))
  .catch((err) => {
    console.error('Failed to start server:', err);
    process.exit(1);
  });
