from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''                            # Se OF mudou, busca e copia TODOS os dados da nova OF
                            if _of_edit != _of_atual_item and _of_edit in _ofs_lista:
                                _of_novo = _conn_upd.execute(_text_upd("""
                                    SELECT nome_cliente, numero_pedido, liga,
                                           descricao_peca, numero_modelo,
                                           peso_liquido_kg, valor_unitario,
                                           numero_desenho, norma
                                    FROM ordem_fabricacao WHERE numero_of=:of
                                """), {"of": _of_edit}).fetchone()
                                if _of_novo:
                                    _novo_pu = float(_of_novo[6] or 0)
                                    _novo_pt = _edit_qtd * _novo_pu
                                    _conn_upd.execute(_text_upd("""
                                        UPDATE oe_item SET
                                            num_of       = :num_of,
                                            qtd          = :qtd,
                                            serie        = :serie,
                                            corrida      = :corrida,
                                            certificado  = :cert,
                                            preco_total  = :pt,
                                            nome_cliente = :cli,
                                            num_pedido   = :ped,
                                            liga         = :liga,
                                            descricao    = :descricao,
                                            cod_peca     = :cod_peca,
                                            peso_unit    = :peso,
                                            preco_unit   = :pu
                                        WHERE id = :id
                                    """), {
                                        "id":       _item_d["id"],
                                        "num_of":   _of_edit,
                                        "qtd":      _edit_qtd,
                                        "serie":    _edit_serie,
                                        "corrida":  _edit_corr,
                                        "cert":     _edit_cert,
                                        "pt":       _novo_pt,
                                        "cli":      _of_novo[0] or "",
                                        "ped":      _of_novo[1] or "",
                                        "liga":     _of_novo[2] or "",
                                        "descricao": _of_novo[3] or "",
                                        "cod_peca": _of_novo[4] or "",
                                        "peso":     float(_of_novo[5] or 0),
                                        "pu":       _novo_pu,
                                    })
                                    st.info(f"Dados copiados da OF {_of_edit}: {_of_novo[3] or ''}")
                            else:
                                _conn_upd.execute(_text_upd("""
                                    UPDATE oe_item SET
                                        num_of=:num_of, qtd=:qtd, serie=:serie,
                                        corrida=:corrida, certificado=:cert,
                                        preco_total=:pt
                                    WHERE id=:id
                                """), _upd)'''

NEW = '''                            # Sempre busca e copia dados da OF (corrige dados incorretos tambem)
                            if _of_edit in _ofs_lista:
                                _of_novo = _conn_upd.execute(_text_upd("""
                                    SELECT nome_cliente, numero_pedido, liga,
                                           descricao_peca, numero_modelo,
                                           peso_liquido_kg, valor_unitario,
                                           numero_desenho, norma
                                    FROM ordem_fabricacao WHERE numero_of=:of
                                """), {"of": _of_edit}).fetchone()
                                if _of_novo:
                                    _novo_pu = float(_of_novo[6] or 0)
                                    _novo_pt = _edit_qtd * _novo_pu
                                    _conn_upd.execute(_text_upd("""
                                        UPDATE oe_item SET
                                            num_of       = :num_of,
                                            qtd          = :qtd,
                                            serie        = :serie,
                                            corrida      = :corrida,
                                            certificado  = :cert,
                                            preco_total  = :pt,
                                            nome_cliente = :cli,
                                            num_pedido   = :ped,
                                            liga         = :liga,
                                            descricao    = :descricao,
                                            cod_peca     = :cod_peca,
                                            peso_unit    = :peso,
                                            preco_unit   = :pu
                                        WHERE id = :id
                                    """), {
                                        "id":        _item_d["id"],
                                        "num_of":    _of_edit,
                                        "qtd":       _edit_qtd,
                                        "serie":     _edit_serie,
                                        "corrida":   _edit_corr,
                                        "cert":      _edit_cert,
                                        "pt":        _novo_pt,
                                        "cli":       _of_novo[0] or "",
                                        "ped":       _of_novo[1] or "",
                                        "liga":      _of_novo[2] or "",
                                        "descricao": _of_novo[3] or "",
                                        "cod_peca":  _of_novo[4] or "",
                                        "peso":      float(_of_novo[5] or 0),
                                        "pu":        _novo_pu,
                                    })
                            else:
                                # OF nao encontrada - atualiza apenas campos editaveis
                                _conn_upd.execute(_text_upd("""
                                    UPDATE oe_item SET
                                        num_of=:num_of, qtd=:qtd, serie=:serie,
                                        corrida=:corrida, certificado=:cert,
                                        preco_total=:pt
                                    WHERE id=:id
                                """), _upd)'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Sempre copia dados da OF ao salvar.")
else:
    print("AVISO: Bloco nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Sempre copia dados OF ao salvar OE' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
