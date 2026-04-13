-- =============================================================================
-- Sistema de Fundição — Modelo de dados (PostgreSQL 11+)
-- Arquitetura: um banco físico `fundicao` com dois esquemas lógicos:
--   - fabricacao  → Ordens de Fabricação (OF), OE, Certificados
--   - corridas    → Cadastro de corridas (fusão) + composição química (JSON)
--   - auditoria   → Log de auditoria (INSERT/UPDATE/DELETE)
--
-- Observação: Dois bancos de dados separados no PostgreSQL não permitem FK
-- entre bases; o uso de esquemas mantém o isolamento lógico e a integridade.
--
-- Instalação:
--   1) Como superusuário, conectado ao banco `postgres`, execute:
--        CREATE DATABASE fundicao WITH ENCODING 'UTF8' TEMPLATE = template0;
--   2) Conecte-se ao banco `fundicao` e execute este arquivo completo
--      (ex.: psql -U postgres -d fundicao -f fundicao_schema.sql).
-- =============================================================================

-- Extensões úteis para relatórios e auditoria
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS fabricacao;
CREATE SCHEMA IF NOT EXISTS corridas;
CREATE SCHEMA IF NOT EXISTS auditoria;

-- -----------------------------------------------------------------------------
-- Domínios / convenções
-- -----------------------------------------------------------------------------
COMMENT ON SCHEMA fabricacao IS 'Ordens de fabricação, ordens de entrega e certificados (base para OE e certificados de qualidade).';
COMMENT ON SCHEMA corridas IS 'Corridas de fusão, séries e análise química (JSON).';
COMMENT ON SCHEMA auditoria IS 'Trilha de auditoria (quem, quando, o quê).';

-- -----------------------------------------------------------------------------
-- ESQUEMA FABRICAÇÃO — Ordem de Fabricação (OF)
-- -----------------------------------------------------------------------------
CREATE TABLE fabricacao.ordem_fabricacao (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero_of               VARCHAR(50) NOT NULL,
    numero_nn               VARCHAR(50),
    nome_cliente            VARCHAR(200) NOT NULL,
    data_abertura_pedido    DATE NOT NULL,
    prazo_entrega_pedido    DATE,
    numero_pedido           VARCHAR(80),
    numero_modelo           VARCHAR(80),
    descricao_peca          TEXT,
    numero_desenho          VARCHAR(80),
    peso_liquido_kg         NUMERIC(14, 4),
    peso_bruto_kg           NUMERIC(14, 4),
    liga                    VARCHAR(120),
    norma                   VARCHAR(120),
    qtd_pecas_pedido        INTEGER NOT NULL DEFAULT 0 CHECK (qtd_pecas_pedido >= 0),
    qtd_fundida             INTEGER NOT NULL DEFAULT 0 CHECK (qtd_fundida >= 0),
    qtd_expedida            INTEGER NOT NULL DEFAULT 0 CHECK (qtd_expedida >= 0),
    valor_unitario          NUMERIC(18, 6),
    valor_total             NUMERIC(18, 2),
    condicao_modelo         VARCHAR(200),
    observacoes             TEXT,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fabricacao_of UNIQUE (numero_of)
);

COMMENT ON TABLE fabricacao.ordem_fabricacao IS 'Cabeçalho da Ordem de Fabricação (OF).';
COMMENT ON COLUMN fabricacao.ordem_fabricacao.numero_nn IS 'NN° — identificador interno/sequencial conforme processo da empresa.';

-- OE: uma OF pode ter várias ordens de entrega (número + quantidade)
CREATE TABLE fabricacao.ordem_entrega (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ordem_fabricacao_id     UUID NOT NULL REFERENCES fabricacao.ordem_fabricacao(id) ON DELETE CASCADE,
    numero_oe               VARCHAR(80) NOT NULL,
    qtd_pecas               INTEGER NOT NULL CHECK (qtd_pecas > 0),
    data_prevista           DATE,
    observacao              TEXT,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE fabricacao.ordem_entrega IS 'OE — Ordem de Entrega vinculada à OF (número e quantidade de peças).';

CREATE INDEX idx_fabricacao_oe_of ON fabricacao.ordem_entrega (ordem_fabricacao_id);
CREATE INDEX idx_fabricacao_oe_numero ON fabricacao.ordem_entrega (numero_oe);

-- Certificados: número do certificado e quantidade de peças abrangidas
CREATE TABLE fabricacao.certificado_peca (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ordem_fabricacao_id     UUID NOT NULL REFERENCES fabricacao.ordem_fabricacao(id) ON DELETE CASCADE,
    numero_certificado      VARCHAR(80) NOT NULL,
    qtd_pecas               INTEGER NOT NULL CHECK (qtd_pecas > 0),
    data_emissao            DATE,
    observacao              TEXT,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE fabricacao.certificado_peca IS 'Certificado de qualidade por OF (número e quantidade de peças).';

CREATE INDEX idx_fabricacao_cert_of ON fabricacao.certificado_peca (ordem_fabricacao_id);
CREATE INDEX idx_fabricacao_cert_numero ON fabricacao.certificado_peca (numero_certificado);

CREATE INDEX idx_fabricacao_of_cliente ON fabricacao.ordem_fabricacao (nome_cliente);
CREATE INDEX idx_fabricacao_of_pedido ON fabricacao.ordem_fabricacao (numero_pedido);

-- -----------------------------------------------------------------------------
-- ESQUEMA CORRIDAS — Cadastro de corridas
-- -----------------------------------------------------------------------------
CREATE TABLE corridas.corrida (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data_fusao                  DATE NOT NULL,
    numero_corrida              VARCHAR(50) NOT NULL,
    nome_cliente                VARCHAR(200) NOT NULL,
    ordem_fabricacao_id         UUID REFERENCES fabricacao.ordem_fabricacao(id) ON DELETE SET NULL,
    numero_ordem_fabricacao     VARCHAR(50),
    qtd_pecas_fundidas          INTEGER NOT NULL DEFAULT 0 CHECK (qtd_pecas_fundidas >= 0),
    serie_pecas_fundidas        VARCHAR(500),
    liga                        VARCHAR(120),
    norma                       VARCHAR(120),
    composicao_quimica_pct      JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em               TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE corridas.corrida IS 'Corrida de fusão; composição química em % no JSON (C, Si, Mn, ...).';
COMMENT ON COLUMN corridas.corrida.numero_ordem_fabricacao IS 'Redundância controlada para consulta quando OF ainda não cadastrada no sistema.';
COMMENT ON COLUMN corridas.corrida.composicao_quimica_pct IS
    'Percentuais: C, Si, Mn, P, S, Cr, Ni, Mo, Cu, W, Nb, B, CE, V, Co, Fe, N, Mg. Ex.: {"C":0.25,"Si":1.2,"Mn":0.8}';

-- Unicidade: mesma corrida no mesmo dia pode ter OFs distintas.
-- A combinação (numero_corrida, data_fusao, numero_ordem_fabricacao) é o que deve ser único.
-- NULL em numero_ordem_fabricacao é tratado como valor distinto pelo PostgreSQL,
-- portanto duas corridas sem OF vinculada no mesmo dia ainda são permitidas.
CREATE UNIQUE INDEX uq_corridas_numero_data_of
    ON corridas.corrida (numero_corrida, data_fusao, numero_ordem_fabricacao, serie_pecas_fundidas);

-- -----------------------------------------------------------------
-- MIGRAÇÃO — execute apenas uma vez em bancos já existentes:
-- DROP INDEX IF EXISTS corridas.uq_corridas_numero_data;
-- CREATE UNIQUE INDEX uq_corridas_numero_data_of
--     ON corridas.corrida (numero_corrida, data_fusao, numero_ordem_fabricacao, serie_pecas_fundidas);
-- -----------------------------------------------------------------
CREATE INDEX idx_corridas_of ON corridas.corrida (ordem_fabricacao_id);
CREATE INDEX idx_corridas_cliente ON corridas.corrida (nome_cliente);
CREATE INDEX idx_corridas_composicao_gin ON corridas.corrida USING gin (composicao_quimica_pct);

-- -----------------------------------------------------------------------------
-- Função: validação opcional das chaves conhecidas da composição (não obrigatória)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION corridas.validar_chaves_composicao(j JSONB)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    chaves_permitidas TEXT[] := ARRAY[
        'C','Si','Mn','P','S','Cr','Ni','Mo','Cu','W','Nb','B','CE','V','Co','Fe','N','Mg'
    ];
    k TEXT;
BEGIN
    IF j IS NULL OR j = '{}'::jsonb THEN
        RETURN TRUE;
    END IF;
    FOR k IN SELECT jsonb_object_keys(j)
    LOOP
        IF NOT (k = ANY (chaves_permitidas)) THEN
            RAISE EXCEPTION 'Chave química não permitida na composição: %', k;
        END IF;
    END LOOP;
    RETURN TRUE;
END;
$$;

ALTER TABLE corridas.corrida
    ADD CONSTRAINT ck_corridas_composicao_keys
    CHECK (corridas.validar_chaves_composicao(composicao_quimica_pct));

-- -----------------------------------------------------------------------------
-- AUDITORIA — tabela de log
-- -----------------------------------------------------------------------------
CREATE TABLE auditoria.log_evento (
    id              BIGSERIAL PRIMARY KEY,
    ocorrido_em     TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    schema_name     TEXT NOT NULL,
    table_name      TEXT NOT NULL,
    operacao        CHAR(1) NOT NULL CHECK (operacao IN ('I','U','D')),
    registro_id     TEXT,
    usuario_db      TEXT NOT NULL DEFAULT current_user,
    usuario_app     TEXT,
    dados_antigos   JSONB,
    dados_novos     JSONB
);

COMMENT ON TABLE auditoria.log_evento IS 'Log de auditoria: I=inclusão, U=alteração, D=exclusão.';
CREATE INDEX idx_auditoria_ocorrido ON auditoria.log_evento (ocorrido_em DESC);
CREATE INDEX idx_auditoria_tabela ON auditoria.log_evento (schema_name, table_name);

-- Sessão pode definir contexto da aplicação: SELECT set_config('app.usuario', 'login', false);
CREATE OR REPLACE FUNCTION auditoria.fn_registrar()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auditoria, public
AS $$
DECLARE
    v_old JSONB;
    v_new JSONB;
    v_id  TEXT;
    v_op  CHAR(1);
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_old := to_jsonb(OLD);
        v_new := NULL;
        v_id  := COALESCE(OLD.id::text, OLD::text);
        v_op  := 'D';
    ELSIF TG_OP = 'UPDATE' THEN
        v_old := to_jsonb(OLD);
        v_new := to_jsonb(NEW);
        v_id  := COALESCE(NEW.id::text, OLD.id::text);
        v_op  := 'U';
    ELSE
        v_old := NULL;
        v_new := to_jsonb(NEW);
        v_id  := NEW.id::text;
        v_op  := 'I';
    END IF;

    INSERT INTO auditoria.log_evento (
        schema_name, table_name, operacao, registro_id,
        usuario_app, dados_antigos, dados_novos
    ) VALUES (
        TG_TABLE_SCHEMA,
        TG_TABLE_NAME,
        v_op,
        v_id,
        NULLIF(current_setting('app.usuario', true), ''),
        v_old,
        v_new
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

-- Aplica auditoria às tabelas principais
CREATE TRIGGER tr_aud_ordem_fabricacao
    AFTER INSERT OR UPDATE OR DELETE ON fabricacao.ordem_fabricacao
    FOR EACH ROW EXECUTE PROCEDURE auditoria.fn_registrar();

CREATE TRIGGER tr_aud_ordem_entrega
    AFTER INSERT OR UPDATE OR DELETE ON fabricacao.ordem_entrega
    FOR EACH ROW EXECUTE PROCEDURE auditoria.fn_registrar();

CREATE TRIGGER tr_aud_certificado_peca
    AFTER INSERT OR UPDATE OR DELETE ON fabricacao.certificado_peca
    FOR EACH ROW EXECUTE PROCEDURE auditoria.fn_registrar();

CREATE TRIGGER tr_aud_corrida
    AFTER INSERT OR UPDATE OR DELETE ON corridas.corrida
    FOR EACH ROW EXECUTE PROCEDURE auditoria.fn_registrar();

-- -----------------------------------------------------------------------------
-- Atualização automática de atualizado_em
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.atualizado_em := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER tr_touch_of
    BEFORE UPDATE ON fabricacao.ordem_fabricacao
    FOR EACH ROW EXECUTE PROCEDURE public.touch_updated_at();

CREATE TRIGGER tr_touch_corrida
    BEFORE UPDATE ON corridas.corrida
    FOR EACH ROW EXECUTE PROCEDURE public.touch_updated_at();

-- -----------------------------------------------------------------------------
-- Visões úteis para relatórios (OE e Certificados)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW fabricacao.vw_of_com_totais AS
SELECT
    ofb.id,
    ofb.numero_of,
    ofb.numero_nn,
    ofb.nome_cliente,
    ofb.data_abertura_pedido,
    ofb.prazo_entrega_pedido,
    ofb.numero_pedido,
    ofb.numero_modelo,
    ofb.descricao_peca,
    ofb.numero_desenho,
    ofb.peso_liquido_kg,
    ofb.peso_bruto_kg,
    ofb.liga,
    ofb.norma,
    ofb.qtd_pecas_pedido,
    ofb.qtd_fundida,
    ofb.qtd_expedida,
    ofb.valor_unitario,
    ofb.valor_total,
    ofb.condicao_modelo,
    COALESCE(SUM(oe.qtd_pecas), 0) AS qtd_total_oe,
    COALESCE(SUM(ce.qtd_pecas), 0) AS qtd_total_certificado
FROM fabricacao.ordem_fabricacao AS ofb
LEFT JOIN fabricacao.ordem_entrega oe ON oe.ordem_fabricacao_id = ofb.id
LEFT JOIN fabricacao.certificado_peca ce ON ce.ordem_fabricacao_id = ofb.id
GROUP BY ofb.id;

COMMENT ON VIEW fabricacao.vw_of_com_totais IS 'OF com totais agregados de OE e certificados para conferência de relatórios.';

-- -----------------------------------------------------------------------------
-- Exemplo de uso (comentado)
-- -----------------------------------------------------------------------------
/*
SELECT set_config('app.usuario', 'joao.silva', false);

INSERT INTO fabricacao.ordem_fabricacao (
    numero_of, numero_nn, nome_cliente, data_abertura_pedido, prazo_entrega_pedido,
    numero_pedido, numero_modelo, descricao_peca, numero_desenho,
    peso_liquido_kg, peso_bruto_kg, liga, norma,
    qtd_pecas_pedido, qtd_fundida, qtd_expedida,
    valor_unitario, valor_total, condicao_modelo
) VALUES (
    'OF-2026-0001', 'NN-001', 'Cliente ABC', '2026-04-01', '2026-05-15',
    'PED-7788', 'MOD-12', 'Flange 4"', 'DWG-4412',
    12.5, 13.1, 'FCD 450-10', 'NBR 6675',
    100, 0, 0,
    150.00, 15000.00, 'Modelo em bom estado'
) RETURNING id;

INSERT INTO fabricacao.ordem_entrega (ordem_fabricacao_id, numero_oe, qtd_pecas)
VALUES ('<uuid-da-of>', 'OE-2026-0100', 40);

INSERT INTO fabricacao.certificado_peca (ordem_fabricacao_id, numero_certificado, qtd_pecas, data_emissao)
VALUES ('<uuid-da-of>', 'CQ-2026-8899', 40, '2026-04-10');

INSERT INTO corridas.corrida (
    data_fusao, numero_corrida, nome_cliente, ordem_fabricacao_id, numero_ordem_fabricacao,
    qtd_pecas_fundidas, serie_pecas_fundidas, liga, norma, composicao_quimica_pct
) VALUES (
    '2026-04-05', 'C-0426', 'Cliente ABC', '<uuid-da-of>', 'OF-2026-0001',
    50, 'Série A001-A050', 'FCD 450-10', 'NBR 6675',
    '{"C":3.45,"Si":2.1,"Mn":0.35,"Mg":0.04,"CE":4.2}'::jsonb
);

SELECT * FROM auditoria.log_evento ORDER BY id DESC LIMIT 20;
*/
