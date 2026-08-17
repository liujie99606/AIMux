-- 保留每种协议类型的一个既有默认模型，再约束后续写入最多一个默认模型。
UPDATE models
SET is_default = 0
WHERE is_default = 1
  AND id NOT IN (
      SELECT id
      FROM (
          SELECT id,
                 ROW_NUMBER() OVER (PARTITION BY type ORDER BY lower(name), id) AS row_number
          FROM models
          WHERE is_default = 1
      )
      WHERE row_number = 1
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_models_one_default_per_type
ON models(type)
WHERE is_default = 1;
