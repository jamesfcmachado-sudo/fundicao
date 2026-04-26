@echo off
echo ============================================================
echo  LIMPEZA DA PASTA - Sistema de Fundicao Metalpoli
echo  Removendo arquivos debug_ e fix_ temporarios
echo ============================================================
echo.
echo ATENCAO: Este script vai excluir todos os arquivos de debug
echo e patches temporarios. Os arquivos essenciais serao mantidos.
echo.
pause

cd /d "C:\Users\james\OneDrive\Área de Trabalho\CURSOR"

echo Excluindo arquivos debug_...
del /q debug_aba_logo.py
del /q debug_all_keys.py
del /q debug_alterar.py
del /q debug_app.py
del /q debug_app2.py
del /q debug_atualizar_ofs.py
del /q debug_atualizar_ofs2.py
del /q debug_auth_dup.py
del /q debug_botoes.py
del /q debug_btn_atualizar.py
del /q debug_cert_auto.py
del /q debug_cert_fields.py
del /q debug_cert_fields2.py
del /q debug_certs_import.py
del /q debug_certs2.py
del /q debug_consulta_tipo.py
del /q debug_consulta2.py
del /q debug_contexto.py
del /q debug_contexto2.py
del /q debug_corridas.py
del /q debug_dup_keys.py
del /q debug_empresa_config.py
del /q debug_fmt_num.py
del /q debug_form_cert.py
del /q debug_gerar_oe.py
del /q debug_importar.py
del /q debug_inicio_app.py
del /q debug_itens_cert.py
del /q debug_itens2.py
del /q debug_keys_form.py
del /q debug_linha629.py
del /q debug_linha3665.py
del /q debug_linhas620.py
del /q debug_logo_cert.py
del /q debug_logo_cert2.py
del /q debug_logo_config.py
del /q debug_logo_dup.py
del /q debug_logo_keys.py
del /q debug_menu.py
del /q debug_novo_cert.py
del /q debug_novo_cert2.py
del /q debug_pdf_atual.py
del /q debug_pdf_blocos.py
del /q debug_pdf_btn.py
del /q debug_pdf_btn2.py
del /q debug_pdf_btn3.py
del /q debug_pdf_cache.py
del /q debug_pdf_cert.py
del /q debug_pdf_state.py
del /q debug_proximo_num.py
del /q debug_salvar_cert.py
del /q debug_segundo_botao.py
del /q debug_session_text.py
del /q debug_tmpl_custom.py
del /q debug_todas_dup.py

echo Excluindo backups e patches do app...
del /q app_auth_backup.py
del /q app_auth_patch.py
del /q app_pg_backup.py
del /q app_pg_patch.py
del /q app_relatorios_perm_backup.py
del /q app_relatorios_perm_patch.py

echo Excluindo arquivos fix_...
del /q fix_add_certs_import.py
del /q fix_admin_config_tab.py
del /q fix_alterar_cert.py
del /q fix_alterar_item_oe.py
del /q fix_alterar_oe_campos.py
del /q fix_alterar_of_oe.py
del /q fix_atualizar_importacao.py
del /q fix_atualizar_ofs_session.py
del /q fix_bairro_config.py
del /q fix_botoes_pdf_excel.py
del /q fix_cab_v2.py
del /q fix_cabecalho_cert.py
del /q fix_cert_auto.py
del /q fix_cert_autocomplete.py
del /q fix_cert_campos.py
del /q fix_cert_of_session.py
del /q fix_certs_ok.py
del /q fix_comp_data_editor.py
del /q fix_comp_session.py
del /q fix_comp_values.py
del /q fix_composicao_cert.py
del /q fix_config_empresa.py
del /q fix_consulta_oes.py
del /q fix_consulta_oes_v2.py
del /q fix_contato_responsavel.py
del /q fix_copiar_dados_of.py
del /q fix_corrida.py
del /q fix_corridas_cert.py
del /q fix_corridas_sem_rerun.py
del /q fix_corridas_slider.py
del /q fix_corridas_v2.py
del /q fix_db_path.py
del /q fix_decimais_norma.py
del /q fix_docstring.py
del /q fix_edicao_cert.py
del /q fix_escopo_certs.py
del /q fix_estrutura_try.py
del /q fix_excel_to_pdf.py
del /q fix_excluir_corrida.py
del /q fix_excluir_of.py
del /q fix_expansor_cert.py
del /q fix_fontsize_pdf.py
del /q fix_force_deploy.py
del /q fix_force_redeploy.py
del /q fix_force_v3.py
del /q fix_future_import.py
del /q fix_gerar_oe_filtro.py
del /q fix_gerar_oe_template.py
del /q fix_historico_oe.py
del /q fix_iframe_syntax.py
del /q fix_import_cert_definitivo.py
del /q fix_importar_oes_certs.py
del /q fix_indent.py
del /q fix_indent_slider.py
del /q fix_init_cert_tables.py
del /q fix_insert_corrida_v2.py
del /q fix_integrar_certificados.py
del /q fix_itens_cert.py
del /q fix_itens_session.py
del /q fix_keys_tmpl.py
del /q fix_layout_cert.py
del /q fix_logo_cert.py
del /q fix_logo_cert_v2.py
del /q fix_logo_e_pdf.py
del /q fix_menu_certs.py
del /q fix_modo_edicao.py
del /q fix_mover_alterar_excluir.py
del /q fix_norm_tipo_imediata.py
del /q fix_norma_da_of.py
del /q fix_nova_oe_completa.py
del /q fix_oe_alterar_excluir.py
del /q fix_oe_alterar_excluir_v2.py
del /q fix_oe_logo.py
del /q fix_oe_pdf.py
del /q fix_oe_somente_pdf.py
del /q fix_oe_ux_alterar.py
del /q fix_of_digitavel.py
del /q fix_ordenacao.py
del /q fix_orientacao_template.py
del /q fix_orientacao_template2.py
del /q fix_orientacao_v2.py
del /q fix_orphan_lines.py
del /q fix_pdf_all_strings.py
del /q fix_pdf_cert_completo.py
del /q fix_pdf_cert_v2.py
del /q fix_pdf_cert_v3.py
del /q fix_pdf_fiel.py
del /q fix_pdf_layout_final.py
del /q fix_pdf_syntax.py
del /q fix_pdf_viewer.py
del /q fix_perm.py
del /q fix_perm_ocultar.py
del /q fix_progress_todos.py
del /q fix_progress_v2.py
del /q fix_proximo_num_oe.py
del /q fix_query_corridas.py
del /q fix_remove_botao2.py
del /q fix_remove_dup_linhas.py
del /q fix_remove_duplicata.py
del /q fix_remove_logo_dup.py
del /q fix_remove_msg_alterar.py
del /q fix_remove_oe_cert.py
del /q fix_remove_segundo_botao.py
del /q fix_remove_tmpl_dup.py
del /q fix_remove_visualizar.py
del /q fix_sel_corr.py
del /q fix_sel_of.py
del /q fix_sempre_copiar_of.py
del /q fix_session_todos.py
del /q fix_session_todos_v2.py
del /q fix_sheet_properties.py
del /q fix_sheet_v2.py
del /q fix_show_pdf_final.py
del /q fix_slider_final.py
del /q fix_slider_v2.py
del /q fix_tabelas_altura.py
del /q fix_tabelas2.py
del /q fix_template_oe.py
del /q fix_templates_custom.py
del /q fix_templates_v2.py
del /q fix_templates_v3.py
del /q fix_tipo_cert.py
del /q fix_tipo_metric.py
del /q fix_tipo_string.py
del /q fix_try_except_oe.py
del /q fix_validacao_corrida2.py
del /q fix_visualizar_final.py
del /q fix_visualizar_pdf.py
del /q fix_visualizar_pdf_v2.py
del /q fix_visualizar_pdf_v3.py
del /q fix_visualizar_session.py

echo Excluindo utilitarios ja incorporados...
del /q check_status.py
del /q corrigir_datas_oe.py
del /q importar_oes_historicas.py
del /q migrar_sqlite_para_postgres.py
del /q migrar_status_of.py

echo.
echo ============================================================
echo  LIMPEZA CONCLUIDA!
echo.
echo  Arquivos mantidos (essenciais):
echo    app.py
echo    certificados.py
echo    empresa_config.py
echo    fundicao_db.py
echo    auth.py
echo    database.py
echo    fundicao_schema.sql
echo    fundicao.db
echo    requirements.txt
echo    gerar_oe_excel.py
echo    sqlite_models.py
echo    Ordem_de_Entrega_2019_a_2023.xlsx
echo    Ordem_de_Entrega_2024_a_2026.xlsx
echo ============================================================
echo.
pause
