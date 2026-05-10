import pandas as pd
import re

def validar_eventos(df):
    resultados = []
    
    # 1. Validaciones ESTRUCTURALES
    columnas_requeridas = ["tipo_evento", "usuario_origen", "usuario_destino", "timestamp"]
    for col in columnas_requeridas:
        resultados.append(col in df.columns) # expect_column_to_exist
        
    resultados.append(df["tipo_evento"].notnull().all()) # expect_column_values_to_not_be_null
    resultados.append(df["usuario_destino"].notnull().all()) # expect_column_values_to_not_be_null

    # 2. Validaciones SEMÁNTICAS
    tipos_validos = ["like", "comentario", "seguidor"]
    resultados.append(df["tipo_evento"].isin(tipos_validos).all()) # expect_column_values_to_be_in_set
    
    # Validar que usuario_origen no sea string vacío
    resultados.append(df["usuario_origen"].str.len().gt(0).all()) # expect_column_values_to_not_match_regex

    # Cálculo de estadísticas
    total = len(resultados)
    ok = sum(1 for r in resultados if r)
    pct = (ok / total) * 100

    print(f"\n{'='*45}")
    print(f" RESULTADO DE VALIDACIÓN - Calidad de Datos")
    print(f"{'='*45}")
    print(f" Expectativas evaluadas : {total}")
    print(f" Exitosas               : {ok}")
    print(f" Fallidas               : {total - ok}")
    print(f" Porcentaje de éxito    : {pct:.1f}%")
    print(f"{'='*45}")

    if pct == 100.0:
        print(" ✓ TODOS LOS DATOS SON VÁLIDOS")
    else:
        print(" ⚠ HAY DATOS QUE NO PASARON VALIDACIÓN")
    
    return ok == total

if __name__ == '__main__':
    df_prueba = pd.DataFrame([
        {"tipo_evento":"like","usuario_origen":"user_001","usuario_destino":"user_042","publicacion_id":"post_789","timestamp":"2025-05-07T10:32:01Z"},
        {"tipo_evento":"comentario","usuario_origen":"user_005","usuario_destino":"user_060","publicacion_id":"post_200","timestamp":"2025-05-07T10:34:00Z"},
    ])
    validar_eventos(df_prueba)