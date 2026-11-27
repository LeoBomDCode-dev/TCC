"""API do pombo-tech: catálogo de hardware e periféricos usados."""
import json
import sqlite3
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import get_db, init_db

Condicao = Literal["excelente", "bom", "marcas_de_uso"]
Status = Literal["disponivel", "reservado", "vendido"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="pombo-tech API", lifespan=lifespan)

# Permite que o frontend (Live Server, porta 5500) chame a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Schemas ----------
class ProdutoIn(BaseModel):
    nome: str = Field(min_length=3, max_length=120)
    descricao: str = ""
    categoria_id: int
    marca: str = Field(min_length=1, max_length=60)
    preco: float = Field(gt=0)
    condicao: Condicao
    garantia_dias: int = Field(default=0, ge=0)
    testado: bool = True
    especificacoes: dict[str, str] = {}
    imagem_url: Optional[str] = None
    status: Status = "disponivel"


# ---------- Helpers ----------
SELECT_PRODUTO = """
    SELECT p.*, c.nome AS categoria_nome, c.slug AS categoria_slug
    FROM produtos p JOIN categorias c ON c.id = p.categoria_id
"""


def row_to_produto(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["especificacoes"] = json.loads(d["especificacoes"])
    d["testado"] = bool(d["testado"])
    return d


def get_produto_or_404(db: sqlite3.Connection, produto_id: int) -> dict:
    row = db.execute(SELECT_PRODUTO + " WHERE p.id = ?", (produto_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Produto não encontrado")
    return row_to_produto(row)


def check_categoria(db: sqlite3.Connection, categoria_id: int) -> None:
    if db.execute("SELECT 1 FROM categorias WHERE id = ?", (categoria_id,)).fetchone() is None:
        raise HTTPException(422, "Categoria inexistente")


# ---------- Rotas: categorias ----------
@app.get("/categorias")
def listar_categorias(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        """
        SELECT c.id, c.nome, c.slug,
               COUNT(p.id) AS total_disponiveis
        FROM categorias c
        LEFT JOIN produtos p ON p.categoria_id = c.id AND p.status = 'disponivel'
        GROUP BY c.id ORDER BY c.nome
        """
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Rotas: produtos ----------
@app.get("/produtos")
def listar_produtos(
    categoria: Optional[str] = Query(None, description="slug da categoria, ex: placa-de-video"),
    marca: Optional[str] = None,
    condicao: Optional[Condicao] = None,
    preco_min: Optional[float] = Query(None, ge=0),
    preco_max: Optional[float] = Query(None, ge=0),
    busca: Optional[str] = Query(None, description="texto livre: nome, marca ou descrição"),
    status: Status = "disponivel",
    ordenar: Literal["recentes", "menor_preco", "maior_preco"] = "recentes",
    pagina: int = Query(1, ge=1),
    limite: int = Query(12, ge=1, le=60),
    db: sqlite3.Connection = Depends(get_db),
):
    where, params = ["p.status = ?"], [status]

    if categoria:
        where.append("c.slug = ?")
        params.append(categoria)
    if marca:
        where.append("LOWER(p.marca) = LOWER(?)")
        params.append(marca)
    if condicao:
        where.append("p.condicao = ?")
        params.append(condicao)
    if preco_min is not None:
        where.append("p.preco >= ?")
        params.append(preco_min)
    if preco_max is not None:
        where.append("p.preco <= ?")
        params.append(preco_max)
    if busca:
        where.append("(p.nome LIKE ? OR p.marca LIKE ? OR p.descricao LIKE ?)")
        params += [f"%{busca}%"] * 3

    order = {
        "recentes": "p.criado_em DESC, p.id DESC",
        "menor_preco": "p.preco ASC",
        "maior_preco": "p.preco DESC",
    }[ordenar]
    where_sql = " WHERE " + " AND ".join(where)

    total = db.execute(
        "SELECT COUNT(*) FROM produtos p JOIN categorias c ON c.id = p.categoria_id" + where_sql,
        params,
    ).fetchone()[0]

    rows = db.execute(
        SELECT_PRODUTO + where_sql + f" ORDER BY {order} LIMIT ? OFFSET ?",
        params + [limite, (pagina - 1) * limite],
    ).fetchall()

    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "itens": [row_to_produto(r) for r in rows],
    }


@app.get("/marcas")
def listar_marcas(db: sqlite3.Connection = Depends(get_db)):
    """Marcas com produtos disponíveis (para montar o filtro)."""
    rows = db.execute(
        "SELECT DISTINCT marca FROM produtos WHERE status = 'disponivel' ORDER BY marca"
    ).fetchall()
    return [r["marca"] for r in rows]


@app.get("/produtos/{produto_id}")
def obter_produto(produto_id: int, db: sqlite3.Connection = Depends(get_db)):
    return get_produto_or_404(db, produto_id)


# TODO (passo 5): proteger as rotas abaixo para que só o admin consiga usar.
@app.post("/produtos", status_code=201)
def criar_produto(dados: ProdutoIn, db: sqlite3.Connection = Depends(get_db)):
    check_categoria(db, dados.categoria_id)
    cur = db.execute(
        """
        INSERT INTO produtos (nome, descricao, categoria_id, marca, preco, condicao,
                              garantia_dias, testado, especificacoes, imagem_url, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (dados.nome, dados.descricao, dados.categoria_id, dados.marca, dados.preco,
         dados.condicao, dados.garantia_dias, int(dados.testado),
         json.dumps(dados.especificacoes, ensure_ascii=False), dados.imagem_url, dados.status),
    )
    db.commit()
    return get_produto_or_404(db, cur.lastrowid)


@app.put("/produtos/{produto_id}")
def atualizar_produto(produto_id: int, dados: ProdutoIn, db: sqlite3.Connection = Depends(get_db)):
    get_produto_or_404(db, produto_id)
    check_categoria(db, dados.categoria_id)
    db.execute(
        """
        UPDATE produtos SET nome=?, descricao=?, categoria_id=?, marca=?, preco=?, condicao=?,
               garantia_dias=?, testado=?, especificacoes=?, imagem_url=?, status=?
        WHERE id=?
        """,
        (dados.nome, dados.descricao, dados.categoria_id, dados.marca, dados.preco,
         dados.condicao, dados.garantia_dias, int(dados.testado),
         json.dumps(dados.especificacoes, ensure_ascii=False), dados.imagem_url,
         dados.status, produto_id),
    )
    db.commit()
    return get_produto_or_404(db, produto_id)


@app.delete("/produtos/{produto_id}", status_code=204)
def remover_produto(produto_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_produto_or_404(db, produto_id)
    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()