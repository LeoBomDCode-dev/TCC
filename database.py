"""Conexão com o SQLite e criação das tabelas."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "pombotech.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Dependência do FastAPI: abre uma conexão por requisição e fecha no fim."""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS categorias (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nome  TEXT NOT NULL UNIQUE,
            slug  TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS produtos (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nome           TEXT    NOT NULL,
            descricao      TEXT    NOT NULL DEFAULT '',
            categoria_id   INTEGER NOT NULL REFERENCES categorias(id),
            marca          TEXT    NOT NULL,
            preco          REAL    NOT NULL CHECK (preco > 0),
            condicao       TEXT    NOT NULL
                           CHECK (condicao IN ('excelente', 'bom', 'marcas_de_uso')),
            garantia_dias  INTEGER NOT NULL DEFAULT 0,
            testado        INTEGER NOT NULL DEFAULT 1,
            especificacoes TEXT    NOT NULL DEFAULT '{}',   -- JSON
            imagem_url     TEXT,
            status         TEXT    NOT NULL DEFAULT 'disponivel'
                           CHECK (status IN ('disponivel', 'reservado', 'vendido')),
            criado_em      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria_id);
        CREATE INDEX IF NOT EXISTS idx_produtos_status    ON produtos(status);
        """
    )
    conn.commit()
    conn.close()