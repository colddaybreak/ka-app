-- AlterTable
ALTER TABLE "knowledge_bases" ADD COLUMN "metadata_schema" JSONB;

-- AlterTable
ALTER TABLE "documents" ADD COLUMN "metadata" JSONB,
ADD COLUMN "metadata_auto_extract" BOOLEAN NOT NULL DEFAULT false;
